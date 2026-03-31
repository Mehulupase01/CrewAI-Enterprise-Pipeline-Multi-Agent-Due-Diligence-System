from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.domain.models import (
    ArrWaterfallItem,
    ChecklistAutoUpdate,
    ChecklistItemStatus,
    ComplianceStatus,
    TechSaasMetricsSummary,
)
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.services.commercial_service import CommercialService
from crewai_enterprise_pipeline_api.services.cyber_service import CyberService
from crewai_enterprise_pipeline_api.services.operations_service import OperationsService
from crewai_enterprise_pipeline_api.services.sector_signal_utils import (
    collect_sector_text,
    extract_amount,
    extract_months,
    extract_percentage,
)

COMPLETED_CHECKLIST_STATUSES = {
    ChecklistItemStatus.SATISFIED.value,
    ChecklistItemStatus.NOT_APPLICABLE.value,
}


class TechSaaSService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)
        self.commercial_service = CommercialService(session)
        self.cyber_service = CyberService(session)
        self.operations_service = OperationsService(session)

    async def build_tech_saas_metrics(
        self,
        case_id: str,
        *,
        persist_checklist: bool = True,
    ) -> TechSaasMetricsSummary | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        commercial_summary = await self.commercial_service.build_commercial_summary(
            case_id,
            persist_checklist=False,
        )
        operations_summary = await self.operations_service.build_operations_summary(
            case_id,
            persist_checklist=False,
        )
        cyber_summary = await self.cyber_service.build_cyber_summary(
            case_id,
            persist_checklist=False,
        )

        text = collect_sector_text(
            case,
            keywords=(
                "arr",
                "mrr",
                "annual recurring revenue",
                "monthly recurring revenue",
                "net revenue retention",
                "nrr",
                "churn",
                "ltv",
                "cac",
                "payback",
                "implementation",
                "delivery",
                "soc 2",
            ),
            workstream_domains=("commercial", "operations", "cyber_privacy"),
            document_kind_keywords=("commercial", "revenue", "kpi", "cyber", "operations"),
        )

        arr = extract_amount(text, "ending arr", "annual recurring revenue")
        mrr = extract_amount(text, "monthly recurring revenue", "mrr")
        if arr is None and mrr is not None:
            arr = round(mrr * 12, 4)
        if mrr is None and arr is not None:
            mrr = round(arr / 12, 4)

        nrr = extract_percentage(text, "net revenue retention", "nrr")
        if nrr is None and commercial_summary is not None:
            nrr = commercial_summary.net_revenue_retention

        churn_rate = extract_percentage(
            text,
            "gross churn",
            "customer churn",
            "logo churn",
            "churn",
        )
        if churn_rate is None and commercial_summary is not None:
            churn_rate = commercial_summary.churn_rate

        ltv = extract_amount(text, "ltv", "lifetime value")
        cac = extract_amount(text, "cac", "customer acquisition cost")
        payback_months = extract_months(text, "payback", "cac payback")

        arr_waterfall = self._build_arr_waterfall(text, arr)
        flags = self._build_flags(
            commercial_summary,
            operations_summary,
            cyber_summary,
            nrr=nrr,
            churn_rate=churn_rate,
            payback_months=payback_months,
        )

        summary = TechSaasMetricsSummary(
            case_id=case_id,
            arr=arr,
            mrr=mrr,
            nrr=nrr,
            churn_rate=churn_rate,
            ltv=ltv,
            cac=cac,
            payback_months=payback_months,
            arr_waterfall=arr_waterfall,
            flags=flags,
        )
        if persist_checklist:
            summary.checklist_updates = await self._auto_update_checklist(
                case,
                summary,
                commercial_summary=commercial_summary,
                operations_summary=operations_summary,
                cyber_summary=cyber_summary,
            )
        return summary

    def _build_arr_waterfall(self, text: str, arr: float | None) -> list[ArrWaterfallItem]:
        mappings = (
            ("Beginning ARR", "beginning arr", "opening arr"),
            ("New ARR", "new arr"),
            ("Expansion ARR", "expansion arr"),
            ("Contraction ARR", "contraction arr"),
            ("Churned ARR", "churned arr"),
            ("Ending ARR", "ending arr", "annual recurring revenue"),
        )
        items: list[ArrWaterfallItem] = []
        for label, *keywords in mappings:
            amount = extract_amount(text, *keywords)
            if amount is None:
                continue
            items.append(
                ArrWaterfallItem(
                    label=label,
                    amount=amount,
                    note=f"{label} derived from sector evidence.",
                )
            )
        if not items and arr is not None:
            items.append(
                ArrWaterfallItem(
                    label="Ending ARR",
                    amount=arr,
                    note="ARR derived from sector evidence without full waterfall breakdown.",
                )
            )
        return items

    def _build_flags(
        self,
        commercial_summary,
        operations_summary,
        cyber_summary,
        *,
        nrr: float | None,
        churn_rate: float | None,
        payback_months: float | None,
    ) -> list[str]:
        flags: list[str] = []
        if nrr is not None and nrr < 1.0:
            flags.append("NRR is below 100%, indicating contraction inside the installed base.")
        if churn_rate is not None and churn_rate > 0.08:
            flags.append("Churn exceeds 8%, which weakens subscription durability.")
        if payback_months is not None and payback_months > 18:
            flags.append("CAC payback exceeds 18 months, creating unit-economics pressure.")
        if commercial_summary is not None and commercial_summary.concentration_signals:
            top_signal = commercial_summary.concentration_signals[0]
            if top_signal.share_of_revenue >= 0.35:
                flags.append(
                    "Top customer concentration remains elevated at "
                    f"{top_signal.share_of_revenue:.0%}."
                )
        if operations_summary is not None and operations_summary.key_person_dependencies:
            flags.append(
                "Delivery remains dependent on named implementation or founder-linked personnel."
            )
        if cyber_summary is not None:
            non_compliant = [
                item
                for item in cyber_summary.controls
                if item.status in {
                    ComplianceStatus.NON_COMPLIANT,
                    ComplianceStatus.PARTIALLY_COMPLIANT,
                }
            ]
            if non_compliant:
                flags.append(
                    "Privacy/security posture still has "
                    f"{len(non_compliant)} unresolved control gaps."
                )
            if not any("SOC 2" in certification for certification in cyber_summary.certifications):
                flags.append("SOC 2 evidence is absent for a SaaS-style delivery model.")
        return flags[:6]

    async def _auto_update_checklist(
        self,
        case,
        summary: TechSaasMetricsSummary,
        *,
        commercial_summary,
        operations_summary,
        cyber_summary,
    ) -> list[ChecklistAutoUpdate]:
        condition_map = {
            "commercial.customer_concentration": bool(
                summary.arr_waterfall
                or summary.nrr is not None
                or summary.churn_rate is not None
                or (commercial_summary and commercial_summary.concentration_signals)
            ),
            "operations.delivery_model": bool(
                operations_summary
                and (
                    operations_summary.dependency_signals
                    or operations_summary.key_person_dependencies
                )
            ),
            "cyber.privacy_controls": bool(
                cyber_summary
                and (
                    cyber_summary.controls
                    or cyber_summary.certifications
                    or cyber_summary.flags
                )
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
        summary: TechSaasMetricsSummary,
    ) -> str:
        if template_key == "commercial.customer_concentration":
            metric_bits: list[str] = []
            if summary.arr is not None:
                metric_bits.append(f"ARR {summary.arr:.2f}")
            if summary.nrr is not None:
                metric_bits.append(f"NRR {summary.nrr:.0%}")
            if summary.churn_rate is not None:
                metric_bits.append(f"churn {summary.churn_rate:.0%}")
            details = ", ".join(metric_bits) if metric_bits else "sector metrics available"
            return f"Auto-satisfied by Phase 12 Tech/SaaS engine with {details}."
        if template_key == "operations.delivery_model":
            return (
                "Auto-satisfied by Phase 12 Tech/SaaS engine with "
                "delivery-dependency review."
            )
        if template_key == "cyber.privacy_controls":
            return (
                "Auto-satisfied by Phase 12 Tech/SaaS engine with "
                "privacy/control posture review."
            )
        return "Auto-satisfied by Phase 12 Tech/SaaS engine."
