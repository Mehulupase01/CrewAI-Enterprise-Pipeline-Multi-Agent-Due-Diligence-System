from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.domain.models import (
    ChecklistAutoUpdate,
    ChecklistItemStatus,
    FlagSeverity,
    VendorQuestionnaireItem,
    VendorRiskTier,
    VendorScoreBreakdownItem,
)
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.services.commercial_service import CommercialService
from crewai_enterprise_pipeline_api.services.cyber_service import CyberService
from crewai_enterprise_pipeline_api.services.financial_qoe_service import FinancialQoEService
from crewai_enterprise_pipeline_api.services.forensic_service import ForensicService
from crewai_enterprise_pipeline_api.services.operations_service import OperationsService
from crewai_enterprise_pipeline_api.services.regulatory_service import RegulatoryService

COMPLETED_CHECKLIST_STATUSES = {
    ChecklistItemStatus.SATISFIED.value,
    ChecklistItemStatus.NOT_APPLICABLE.value,
}


class VendorService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)
        self.commercial_service = CommercialService(session)
        self.cyber_service = CyberService(session)
        self.financial_service = FinancialQoEService(session)
        self.forensic_service = ForensicService(session)
        self.operations_service = OperationsService(session)
        self.regulatory_service = RegulatoryService(session)

    async def build_vendor_risk_tier(
        self,
        case_id: str,
        *,
        persist_checklist: bool = True,
    ) -> VendorRiskTier | None:
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
        financial_summary = await self.financial_service.build_financial_summary(
            case_id,
            persist_checklist=False,
        )
        forensic_summary = await self.forensic_service.build_forensic_summary(
            case_id,
            persist_checklist=False,
        )
        compliance_summary = await self.regulatory_service.build_compliance_matrix(
            case_id,
            persist_checklist=False,
        )

        breakdown = self._build_breakdown(
            case,
            commercial_summary,
            operations_summary,
            cyber_summary,
            financial_summary,
            forensic_summary,
            compliance_summary,
        )
        overall_score = round(
            sum(item.score * item.weight for item in breakdown)
            / max(sum(item.weight for item in breakdown), 1.0)
        )
        tier = self._tier_for_score(overall_score)
        questionnaire = self._build_questionnaire(
            case, cyber_summary, compliance_summary, operations_summary, forensic_summary
        )
        certifications_required = self._required_certifications(cyber_summary, tier)
        flags = self._build_flags(tier, breakdown, questionnaire, certifications_required)

        summary = VendorRiskTier(
            case_id=case_id,
            tier=tier,
            overall_score=overall_score,
            scoring_breakdown=breakdown,
            questionnaire=questionnaire,
            certifications_required=certifications_required,
            next_review_date=self._next_review_date(tier),
            flags=flags,
        )
        if persist_checklist:
            summary.checklist_updates = await self._auto_update_checklist(case, summary)
        return summary

    def _build_breakdown(
        self,
        case,
        commercial_summary,
        operations_summary,
        cyber_summary,
        financial_summary,
        forensic_summary,
        compliance_summary,
    ) -> list[VendorScoreBreakdownItem]:
        breakdown: list[VendorScoreBreakdownItem] = []
        breakdown.append(
            VendorScoreBreakdownItem(
                factor="service_criticality",
                score=self._criticality_score(commercial_summary, operations_summary),
                weight=0.15,
                rationale=(
                    "Criticality reflects dependency concentration, resilience, "
                    "and single-vendor exposure."
                ),
            )
        )
        breakdown.append(
            VendorScoreBreakdownItem(
                factor="regulatory_screening",
                score=self._regulatory_score(case, compliance_summary),
                weight=0.15,
                rationale=(
                    "Regulatory score reflects watchlist, licensing, and "
                    "unresolved compliance restrictions."
                ),
            )
        )
        breakdown.append(
            VendorScoreBreakdownItem(
                factor="cyber_privacy_posture",
                score=self._cyber_score(cyber_summary),
                weight=0.25,
                rationale=(
                    "Cyber score reflects control maturity, certifications, "
                    "and unresolved privacy gaps."
                ),
            )
        )
        breakdown.append(
            VendorScoreBreakdownItem(
                factor="integrity_risk",
                score=self._integrity_score(case, forensic_summary),
                weight=0.2,
                rationale=(
                    "Integrity score reflects sanctions, conflicts, "
                    "related-party concerns, and misconduct signals."
                ),
            )
        )
        breakdown.append(
            VendorScoreBreakdownItem(
                factor="operational_resilience",
                score=self._operations_score(operations_summary),
                weight=0.15,
                rationale=(
                    "Operational resilience reflects continuity, failover, "
                    "and key-person dependency."
                ),
            )
        )
        breakdown.append(
            VendorScoreBreakdownItem(
                factor="financial_resilience",
                score=self._financial_score(financial_summary),
                weight=0.1,
                rationale=(
                    "Financial resilience reflects basic solvency, cash "
                    "conversion, and distress indicators."
                ),
            )
        )
        return breakdown

    def _build_questionnaire(
        self,
        case,
        cyber_summary,
        compliance_summary,
        operations_summary,
        forensic_summary,
    ) -> list[VendorQuestionnaireItem]:
        items = [
            VendorQuestionnaireItem(
                section="corporate_profile",
                status="complete"
                if any(
                    item.template_key == "legal_corporate.vendor_registration"
                    for item in case.checklist_items
                )
                else "partial",
                detail=(
                    "Corporate profile relies on registration, ownership, and "
                    "signatory evidence in the checklist and issue register."
                ),
            ),
            VendorQuestionnaireItem(
                section="regulatory_screening",
                status="complete" if compliance_summary and compliance_summary.items else "partial",
                detail=(
                    "Regulatory screening covers sanctions, licensing, and "
                    "data-transfer restrictions."
                ),
            ),
            VendorQuestionnaireItem(
                section="security_questionnaire",
                status="complete" if cyber_summary and cyber_summary.controls else "missing",
                detail=(
                    "Security questionnaire coverage reflects control "
                    "responses and attached evidence."
                ),
            ),
            VendorQuestionnaireItem(
                section="business_continuity",
                status="complete"
                if operations_summary and operations_summary.dependency_signals
                else "partial",
                detail=(
                    "Business continuity section covers failover, key-person "
                    "dependencies, and service continuity signals."
                ),
            ),
            VendorQuestionnaireItem(
                section="integrity_screening",
                status="complete" if forensic_summary and forensic_summary.flags else "partial",
                detail=(
                    "Integrity screening covers beneficial ownership, "
                    "conflicts, and misconduct indicators."
                ),
            ),
        ]
        return items

    def _required_certifications(self, cyber_summary, tier: str) -> list[str]:
        required = {"ISO 27001"}
        certifications = set(cyber_summary.certifications if cyber_summary is not None else [])
        if tier in {"tier_1_critical", "tier_2_high"}:
            required.add("SOC 2 Type II")
            required.add("Business Continuity Attestation")
        if cyber_summary is not None and cyber_summary.breach_history:
            required.add("Incident Response Attestation")
        return sorted(required - certifications)

    def _build_flags(
        self,
        tier: str,
        breakdown: list[VendorScoreBreakdownItem],
        questionnaire: list[VendorQuestionnaireItem],
        certifications_required: list[str],
    ) -> list[str]:
        flags = [f"Vendor tier classified as {tier}."]
        weak_factors = [item.factor for item in breakdown if item.score < 60]
        if weak_factors:
            flags.append("Weak scoring areas: " + ", ".join(weak_factors[:4]) + ".")
        incomplete_sections = [item.section for item in questionnaire if item.status != "complete"]
        if incomplete_sections:
            flags.append(
                "Questionnaire follow-up required for: " + ", ".join(incomplete_sections[:4]) + "."
            )
        if certifications_required:
            flags.append(
                "Additional attestations required: " + ", ".join(certifications_required[:4]) + "."
            )
        return flags

    async def _auto_update_checklist(
        self,
        case,
        summary: VendorRiskTier,
    ) -> list[ChecklistAutoUpdate]:
        condition_map = {
            "regulatory.vendor_risk_tier": bool(summary.scoring_breakdown),
            "cyber_privacy.vendor_questionnaire": bool(summary.questionnaire),
            "cyber_privacy.vendor_certifications": True,
            "commercial.vendor_criticality_assessment": bool(summary.scoring_breakdown),
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

    def _build_checklist_note(self, template_key: str, summary: VendorRiskTier) -> str:
        if template_key == "regulatory.vendor_risk_tier":
            return (
                "Auto-satisfied by Phase 11 Vendor engine with tier "
                f"{summary.tier} and score {summary.overall_score}/100."
            )
        if template_key == "cyber_privacy.vendor_questionnaire":
            return (
                "Auto-satisfied by Phase 11 Vendor engine with "
                f"{len(summary.questionnaire)} questionnaire sections."
            )
        if template_key == "cyber_privacy.vendor_certifications":
            return (
                "Auto-satisfied by Phase 11 Vendor engine; remaining required certifications: "
                + (
                    ", ".join(summary.certifications_required)
                    if summary.certifications_required
                    else "none"
                )
            )
        return "Auto-satisfied by Phase 11 Vendor engine."

    def _criticality_score(self, commercial_summary, operations_summary) -> int:
        score = 72
        if commercial_summary is not None and commercial_summary.concentration_signals:
            top_signal = commercial_summary.concentration_signals[0]
            if top_signal.share_of_revenue >= 0.6:
                score -= 15
            elif top_signal.share_of_revenue >= 0.35:
                score -= 8
        if operations_summary is not None:
            if operations_summary.single_site_dependency:
                score -= 10
            score -= min(len(operations_summary.key_person_dependencies) * 4, 10)
        return self._clamp_score(score)

    def _regulatory_score(self, case, compliance_summary) -> int:
        score = 78
        if compliance_summary is not None:
            for item in compliance_summary.items:
                if item.status.value == "non_compliant":
                    score -= 18
                elif item.status.value == "partially_compliant":
                    score -= 8
        relevant_issues = [
            issue
            for issue in case.issues
            if issue.workstream_domain == "regulatory"
            and issue.severity in {FlagSeverity.HIGH.value, FlagSeverity.CRITICAL.value}
        ]
        score -= min(len(relevant_issues) * 8, 20)
        return self._clamp_score(score)

    def _cyber_score(self, cyber_summary) -> int:
        score = 75
        if cyber_summary is None:
            return 40
        non_compliant = [
            item for item in cyber_summary.controls if item.status.value == "non_compliant"
        ]
        partial = [
            item for item in cyber_summary.controls if item.status.value == "partially_compliant"
        ]
        score -= min(len(non_compliant) * 10, 25)
        score -= min(len(partial) * 5, 15)
        if cyber_summary.breach_history:
            score -= min(len(cyber_summary.breach_history) * 6, 12)
        if "ISO 27001" in cyber_summary.certifications:
            score += 6
        if any("SOC 2" in certification for certification in cyber_summary.certifications):
            score += 5
        return self._clamp_score(score)

    def _integrity_score(self, case, forensic_summary) -> int:
        score = 80
        if forensic_summary is not None:
            score -= min(len(forensic_summary.flags) * 12, 35)
        integrity_issues = [
            issue
            for issue in case.issues
            if issue.workstream_domain == "forensic_compliance"
            and issue.severity in {FlagSeverity.HIGH.value, FlagSeverity.CRITICAL.value}
        ]
        score -= min(len(integrity_issues) * 8, 20)
        return self._clamp_score(score)

    def _operations_score(self, operations_summary) -> int:
        score = 74
        if operations_summary is None:
            return 45
        if operations_summary.single_site_dependency:
            score -= 12
        score -= min(len(operations_summary.key_person_dependencies) * 4, 10)
        score -= min(len(operations_summary.dependency_signals) * 2, 10)
        return self._clamp_score(score)

    def _financial_score(self, financial_summary) -> int:
        score = 70
        if financial_summary is None or not financial_summary.periods:
            return 50
        cash_conversion = financial_summary.ratios.get("cash_conversion")
        leverage = financial_summary.ratios.get("debt_to_ebitda")
        if cash_conversion is not None and cash_conversion < 0.4:
            score -= 12
        if leverage is not None and leverage > 4:
            score -= 15
        score -= min(len(financial_summary.flags) * 3, 12)
        return self._clamp_score(score)

    def _tier_for_score(self, score: int) -> str:
        if score < 50:
            return "tier_1_critical"
        if score < 65:
            return "tier_2_high"
        if score < 80:
            return "tier_3_moderate"
        return "tier_4_low"

    def _next_review_date(self, tier: str) -> date:
        today = datetime.now(UTC).date()
        day_offsets = {
            "tier_1_critical": 30,
            "tier_2_high": 90,
            "tier_3_moderate": 180,
            "tier_4_low": 365,
        }
        return today + timedelta(days=day_offsets[tier])

    def _clamp_score(self, score: int) -> int:
        return max(0, min(100, int(round(score))))
