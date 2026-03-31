from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.domain.models import (
    AlmBucketGap,
    BfsiNbfcMetricsSummary,
    ChecklistAutoUpdate,
    ChecklistItemStatus,
    ComplianceStatus,
)
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.services.cyber_service import CyberService
from crewai_enterprise_pipeline_api.services.forensic_service import ForensicService
from crewai_enterprise_pipeline_api.services.operations_service import OperationsService
from crewai_enterprise_pipeline_api.services.regulatory_service import RegulatoryService
from crewai_enterprise_pipeline_api.services.sector_signal_utils import (
    collect_sector_text,
    extract_percentage,
    extract_status_flag,
)

COMPLETED_CHECKLIST_STATUSES = {
    ChecklistItemStatus.SATISFIED.value,
    ChecklistItemStatus.NOT_APPLICABLE.value,
}

ALM_BUCKET_PATTERN = re.compile(
    r"(?P<label>(?:1-30|31-60|61-90|91-180|180\+?)\s*days?)"
    r"[^0-9%]{0,35}(?P<number>\d[\d,]*(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)


class BfsiNbfcService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)
        self.cyber_service = CyberService(session)
        self.forensic_service = ForensicService(session)
        self.operations_service = OperationsService(session)
        self.regulatory_service = RegulatoryService(session)

    async def build_bfsi_nbfc_metrics(
        self,
        case_id: str,
        *,
        persist_checklist: bool = True,
    ) -> BfsiNbfcMetricsSummary | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        cyber_summary = await self.cyber_service.build_cyber_summary(
            case_id,
            persist_checklist=False,
        )
        forensic_summary = await self.forensic_service.build_forensic_summary(
            case_id,
            persist_checklist=False,
        )
        operations_summary = await self.operations_service.build_operations_summary(
            case_id,
            persist_checklist=False,
        )
        compliance_summary = await self.regulatory_service.build_compliance_matrix(
            case_id,
            persist_checklist=False,
        )

        text = collect_sector_text(
            case,
            keywords=(
                "gnpa",
                "gross npa",
                "nnpa",
                "net npa",
                "crar",
                "capital adequacy",
                "alm mismatch",
                "liquidity mismatch",
                "psl compliance",
                "priority sector lending",
                "evergreening",
                "collections",
                "kyc",
                "aml",
                "rbi registration",
            ),
            workstream_domains=(
                "financial_qoe",
                "regulatory",
                "operations",
                "cyber_privacy",
                "forensic_compliance",
            ),
            document_kind_keywords=("rbi", "nbfc", "portfolio", "collections", "alm", "kyc"),
        )

        gnpa = extract_percentage(text, "gross npa", "gnpa")
        nnpa = extract_percentage(text, "net npa", "nnpa")
        crar = extract_percentage(text, "crar", "capital adequacy")
        alm_mismatch = extract_percentage(text, "alm mismatch", "liquidity mismatch")
        psl_compliance = self._extract_psl_status(text, compliance_summary)
        alm_bucket_gaps = self._extract_alm_buckets(text)
        flags = self._build_flags(
            cyber_summary,
            forensic_summary,
            operations_summary,
            compliance_summary,
            text=text,
            gnpa=gnpa,
            nnpa=nnpa,
            crar=crar,
            alm_mismatch=alm_mismatch,
            psl_compliance=psl_compliance,
        )

        summary = BfsiNbfcMetricsSummary(
            case_id=case_id,
            gnpa=gnpa,
            nnpa=nnpa,
            crar=crar,
            alm_mismatch=alm_mismatch,
            psl_compliance=psl_compliance,
            alm_bucket_gaps=alm_bucket_gaps,
            flags=flags,
        )
        if persist_checklist:
            summary.checklist_updates = await self._auto_update_checklist(
                case,
                summary,
                cyber_summary=cyber_summary,
                forensic_summary=forensic_summary,
                operations_summary=operations_summary,
                compliance_summary=compliance_summary,
            )
        return summary

    def _extract_psl_status(self, text: str, compliance_summary) -> ComplianceStatus:
        explicit = extract_status_flag(
            text,
            anchor_keywords=("psl compliance", "priority sector lending"),
            positive_markers=("compliant", "met target", "within target", "no shortfall"),
            negative_markers=("shortfall", "non-compliant", "below target", "breach"),
        )
        if explicit == "positive":
            return ComplianceStatus.COMPLIANT
        if explicit == "negative":
            return ComplianceStatus.NON_COMPLIANT

        if compliance_summary is not None:
            for item in compliance_summary.items:
                regulation = item.regulation.lower()
                if "priority sector" in regulation or "psl" in regulation:
                    return item.status
        return ComplianceStatus.UNKNOWN

    def _extract_alm_buckets(self, text: str) -> list[AlmBucketGap]:
        buckets: list[AlmBucketGap] = []
        seen_buckets: set[tuple[str, float]] = set()
        for match in ALM_BUCKET_PATTERN.finditer(text):
            bucket_label = " ".join(match.group("label").split())
            mismatch_ratio = round(float(match.group("number").replace(",", "")) / 100.0, 6)
            fingerprint = (bucket_label.lower(), mismatch_ratio)
            if fingerprint in seen_buckets:
                continue
            seen_buckets.add(fingerprint)
            buckets.append(
                AlmBucketGap(
                    bucket_label=bucket_label,
                    mismatch_ratio=mismatch_ratio,
                    note="ALM mismatch extracted from sector evidence.",
                )
            )
        return buckets[:6]

    def _build_flags(
        self,
        cyber_summary,
        forensic_summary,
        operations_summary,
        compliance_summary,
        *,
        text: str,
        gnpa: float | None,
        nnpa: float | None,
        crar: float | None,
        alm_mismatch: float | None,
        psl_compliance: ComplianceStatus,
    ) -> list[str]:
        flags: list[str] = []
        if gnpa is not None and gnpa > 0.05:
            flags.append("GNPA exceeds 5%, indicating elevated portfolio stress.")
        if nnpa is not None and nnpa > 0.03:
            flags.append("NNPA exceeds 3%, indicating residual credit-loss pressure.")
        if crar is not None and crar < 0.15:
            flags.append("CRAR is below 15%, leaving limited capital buffer.")
        if alm_mismatch is not None and alm_mismatch > 0.20:
            flags.append("ALM mismatch exceeds 20%, indicating liquidity-gap pressure.")
        if psl_compliance == ComplianceStatus.NON_COMPLIANT:
            flags.append("Priority-sector lending compliance shows a recorded shortfall.")
        if compliance_summary is not None:
            unresolved = [
                item
                for item in compliance_summary.items
                if item.status in {
                    ComplianceStatus.NON_COMPLIANT,
                    ComplianceStatus.PARTIALLY_COMPLIANT,
                }
            ]
            if unresolved:
                flags.append(
                    f"Regulatory matrix still has {len(unresolved)} unresolved RBI/sector items."
                )
        if operations_summary is not None and operations_summary.dependency_signals:
            flags.append(
                "Collections or underwriting governance still depends on key "
                "operating nodes."
            )
        lowered_text = text.lower()
        weak_control_signal = False
        if cyber_summary is not None:
            weak_controls = [
                item
                for item in cyber_summary.controls
                if item.status in {
                    ComplianceStatus.NON_COMPLIANT,
                    ComplianceStatus.PARTIALLY_COMPLIANT,
                }
            ]
            weak_control_signal = bool(weak_controls)
        if not weak_control_signal and (
            any(token in lowered_text for token in ("kyc", "aml", "borrower-data", "data access"))
            and any(
                token in lowered_text
                for token in ("gap", "partial", "review", "override", "exception")
            )
        ):
            weak_control_signal = True
        if weak_control_signal:
            flags.append("KYC/AML or borrower-data controls still have unresolved gaps.")
        if forensic_summary is not None and forensic_summary.flags:
            flags.append("Connected lending or evergreening-style forensic concerns remain open.")
        return flags[:7]

    async def _auto_update_checklist(
        self,
        case,
        summary: BfsiNbfcMetricsSummary,
        *,
        cyber_summary,
        forensic_summary,
        operations_summary,
        compliance_summary,
    ) -> list[ChecklistAutoUpdate]:
        condition_map = {
            "financial_qoe.asset_quality_and_provisioning": bool(
                summary.gnpa is not None or summary.nnpa is not None
            ),
            "financial_qoe.alm_liquidity_profile": bool(
                summary.alm_mismatch is not None or summary.alm_bucket_gaps
            ),
            "regulatory.rbi_registration_and_returns": bool(
                compliance_summary and compliance_summary.items
            ),
            "operations.underwriting_and_collections_governance": bool(
                operations_summary and operations_summary.dependency_signals
            ),
            "cyber_privacy.kyc_aml_and_data_controls": bool(
                cyber_summary and cyber_summary.controls
            ),
            "forensic.connected_lending_and_evergreening": bool(
                forensic_summary and forensic_summary.flags
            ),
        }

        updated: list[ChecklistAutoUpdate] = []
        for item in case.checklist_items:
            template_key = item.template_key or ""
            if not condition_map.get(template_key):
                continue
            if item.status in COMPLETED_CHECKLIST_STATUSES:
                continue
            note = self._build_checklist_note(template_key, summary)
            item.status = ChecklistItemStatus.SATISFIED.value
            item.note = note
            updated.append(
                ChecklistAutoUpdate(
                    checklist_id=item.id,
                    template_key=template_key,
                    status=ChecklistItemStatus.SATISFIED,
                    note=note,
                )
            )
        if updated:
            await self.session.commit()
        return updated

    def _build_checklist_note(
        self,
        template_key: str,
        summary: BfsiNbfcMetricsSummary,
    ) -> str:
        if template_key == "financial_qoe.asset_quality_and_provisioning":
            gnpa = "n/a" if summary.gnpa is None else f"{summary.gnpa:.2%}"
            nnpa = "n/a" if summary.nnpa is None else f"{summary.nnpa:.2%}"
            return (
                "Auto-satisfied by Phase 12 BFSI/NBFC engine with "
                f"GNPA {gnpa} and NNPA {nnpa}."
            )
        if template_key == "financial_qoe.alm_liquidity_profile":
            if summary.alm_mismatch is not None:
                return (
                    "Auto-satisfied by Phase 12 BFSI/NBFC engine with "
                    f"ALM mismatch {summary.alm_mismatch:.2%}."
                )
            return "Auto-satisfied by Phase 12 BFSI/NBFC engine with ALM bucket review."
        if template_key == "regulatory.rbi_registration_and_returns":
            return (
                "Auto-satisfied by Phase 12 BFSI/NBFC engine with "
                "RBI registration/returns review."
            )
        if template_key == "operations.underwriting_and_collections_governance":
            return (
                "Auto-satisfied by Phase 12 BFSI/NBFC engine with "
                "underwriting/collections governance review."
            )
        if template_key == "cyber_privacy.kyc_aml_and_data_controls":
            return "Auto-satisfied by Phase 12 BFSI/NBFC engine with KYC/AML data-control review."
        if template_key == "forensic.connected_lending_and_evergreening":
            return "Auto-satisfied by Phase 12 BFSI/NBFC engine with connected-lending review."
        return "Auto-satisfied by Phase 12 BFSI/NBFC engine."
