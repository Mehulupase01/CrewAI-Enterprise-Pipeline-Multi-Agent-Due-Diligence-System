from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.domain.models import (
    ApprovalDecisionKind,
    ComplianceStatus,
    ExecutiveMemoReport,
    FlagSeverity,
    MotionPack,
    SectorPack,
)
from crewai_enterprise_pipeline_api.services.bfsi_nbfc_service import BfsiNbfcService
from crewai_enterprise_pipeline_api.services.buy_side_service import BuySideService
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.services.checklist_service import ChecklistService
from crewai_enterprise_pipeline_api.services.commercial_service import CommercialService
from crewai_enterprise_pipeline_api.services.credit_service import CreditService
from crewai_enterprise_pipeline_api.services.cyber_service import CyberService
from crewai_enterprise_pipeline_api.services.financial_qoe_service import FinancialQoEService
from crewai_enterprise_pipeline_api.services.forensic_service import ForensicService
from crewai_enterprise_pipeline_api.services.legal_service import LegalService
from crewai_enterprise_pipeline_api.services.manufacturing_service import ManufacturingService
from crewai_enterprise_pipeline_api.services.operations_service import OperationsService
from crewai_enterprise_pipeline_api.services.regulatory_service import RegulatoryService
from crewai_enterprise_pipeline_api.services.tax_service import TaxService
from crewai_enterprise_pipeline_api.services.tech_saas_service import TechSaaSService
from crewai_enterprise_pipeline_api.services.vendor_service import VendorService

SEVERITY_ORDER = {
    FlagSeverity.CRITICAL.value: 0,
    FlagSeverity.HIGH.value: 1,
    FlagSeverity.MEDIUM.value: 2,
    FlagSeverity.LOW.value: 3,
    FlagSeverity.INFO.value: 4,
}


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.bfsi_nbfc_service = BfsiNbfcService(session)
        self.buy_side_service = BuySideService(session)
        self.case_service = CaseService(session)
        self.checklist_service = ChecklistService(session)
        self.commercial_service = CommercialService(session)
        self.credit_service = CreditService(session)
        self.cyber_service = CyberService(session)
        self.financial_qoe_service = FinancialQoEService(session)
        self.forensic_service = ForensicService(session)
        self.legal_service = LegalService(session)
        self.manufacturing_service = ManufacturingService(session)
        self.operations_service = OperationsService(session)
        self.tax_service = TaxService(session)
        self.tech_saas_service = TechSaaSService(session)
        self.regulatory_service = RegulatoryService(session)
        self.vendor_service = VendorService(session)

    async def build_executive_memo(self, case_id: str) -> ExecutiveMemoReport | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        coverage = await self.checklist_service.get_coverage_summary(case_id)
        if coverage is None:
            return None

        sorted_issues = self._sorted_issues(case.issues)
        latest_approval = case.approvals[-1] if case.approvals else None
        approval_state = (
            None if latest_approval is None else ApprovalDecisionKind(latest_approval.decision)
        )
        report_status = (
            "ready_for_export"
            if latest_approval is not None and latest_approval.ready_for_export
            else "not_ready"
        )
        open_requests = [request for request in case.request_items if request.status != "closed"]
        motion_pack = MotionPack(case.motion_pack)
        sector_pack = SectorPack(case.sector_pack)
        report_title = self._report_title_for_motion(motion_pack)
        financial_summary = await self.financial_qoe_service.build_financial_summary(
            case_id,
            persist_checklist=False,
        )
        legal_summary = await self.legal_service.build_legal_summary(
            case_id,
            persist_checklist=False,
        )
        tax_summary = await self.tax_service.build_tax_summary(
            case_id,
            persist_checklist=False,
        )
        compliance_summary = await self.regulatory_service.build_compliance_matrix(
            case_id,
            persist_checklist=False,
        )
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
        forensic_summary = await self.forensic_service.build_forensic_summary(
            case_id,
            persist_checklist=False,
        )
        buy_side_analysis = None
        borrower_scorecard = None
        vendor_risk_tier = None
        tech_saas_metrics = None
        manufacturing_metrics = None
        bfsi_nbfc_metrics = None
        if motion_pack == MotionPack.BUY_SIDE_DILIGENCE:
            buy_side_analysis = await self.buy_side_service.build_buy_side_analysis(
                case_id,
                persist_checklist=False,
            )
        elif motion_pack == MotionPack.CREDIT_LENDING:
            borrower_scorecard = await self.credit_service.build_borrower_scorecard(
                case_id,
                persist_checklist=False,
            )
        elif motion_pack == MotionPack.VENDOR_ONBOARDING:
            vendor_risk_tier = await self.vendor_service.build_vendor_risk_tier(
                case_id,
                persist_checklist=False,
            )
        if sector_pack == SectorPack.TECH_SAAS_SERVICES:
            tech_saas_metrics = await self.tech_saas_service.build_tech_saas_metrics(
                case_id,
                persist_checklist=False,
            )
        elif sector_pack == SectorPack.MANUFACTURING_INDUSTRIALS:
            manufacturing_metrics = await self.manufacturing_service.build_manufacturing_metrics(
                case_id,
                persist_checklist=False,
            )
        elif sector_pack == SectorPack.BFSI_NBFC:
            bfsi_nbfc_metrics = await self.bfsi_nbfc_service.build_bfsi_nbfc_metrics(
                case_id,
                persist_checklist=False,
            )

        executive_summary = self._build_summary(
            motion_pack,
            sector_pack,
            case.name,
            case.target_name,
            len(sorted_issues),
            coverage.open_mandatory_items,
            len(open_requests),
            financial_summary,
            legal_summary,
            tax_summary,
            compliance_summary,
            commercial_summary,
            operations_summary,
            cyber_summary,
            forensic_summary,
            buy_side_analysis,
            borrower_scorecard,
            vendor_risk_tier,
            tech_saas_metrics,
            manufacturing_metrics,
            bfsi_nbfc_metrics,
        )
        motion_pack_highlights = self._build_motion_pack_highlights(
            motion_pack,
            buy_side_analysis,
            borrower_scorecard,
            vendor_risk_tier,
        )
        sector_pack_highlights = self._build_sector_pack_highlights(
            sector_pack,
            tech_saas_metrics,
            manufacturing_metrics,
            bfsi_nbfc_metrics,
        )
        next_actions = self._build_next_actions(
            motion_pack,
            coverage.open_mandatory_items,
            sorted_issues,
            len(open_requests),
            approval_state,
        )

        return ExecutiveMemoReport(
            case_id=case.id,
            case_name=case.name,
            target_name=case.target_name,
            motion_pack=motion_pack,
            sector_pack=sector_pack,
            report_title=report_title,
            generated_at=datetime.now(UTC),
            report_status=report_status,
            approval_state=approval_state,
            executive_summary=executive_summary,
            top_issues=sorted_issues[:5],
            open_requests=open_requests[:5],
            checklist_coverage=coverage,
            motion_pack_highlights=motion_pack_highlights,
            sector_pack_highlights=sector_pack_highlights,
            next_actions=next_actions,
        )

    async def render_executive_memo_markdown(self, case_id: str) -> str | None:
        memo = await self.build_executive_memo(case_id)
        if memo is None:
            return None

        issue_lines = [
            f"- [{issue.severity}] {issue.title}: {issue.business_impact}"
            for issue in memo.top_issues
        ] or ["- No issues have been recorded yet."]
        request_lines = [
            f"- {request.title} ({request.status})" for request in memo.open_requests
        ] or ["- No open diligence requests."]
        next_action_lines = [f"- {action}" for action in memo.next_actions] or [
            "- No immediate next actions recorded."
        ]
        motion_pack_lines = [f"- {item}" for item in memo.motion_pack_highlights] or [
            "- No motion-pack highlights generated yet."
        ]

        return "\n".join(
            [
                f"# {memo.report_title}: {memo.case_name}",
                "",
                f"Target: {memo.target_name}",
                f"Motion Pack: {memo.motion_pack.value}",
                f"Sector Pack: {memo.sector_pack.value}",
                f"Generated: {memo.generated_at.isoformat()}",
                f"Status: {memo.report_status}",
                "",
                "## Summary",
                memo.executive_summary,
                "",
                "## Top Issues",
                *issue_lines,
                "",
                "## Checklist Coverage",
                (f"- Mandatory open items: {memo.checklist_coverage.open_mandatory_items}"),
                f"- Completion ready: {memo.checklist_coverage.completion_ready}",
                "",
                "## Motion Pack Highlights",
                *motion_pack_lines,
                "",
                "## Sector Pack Highlights",
                *([f"- {item}" for item in memo.sector_pack_highlights] or [
                    "- No sector-pack highlights generated yet."
                ]),
                "",
                "## Open Requests",
                *request_lines,
                "",
                "## Next Actions",
                *next_action_lines,
            ]
        )

    async def render_issue_register_markdown(self, case_id: str) -> str | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        sorted_issues = self._sorted_issues(case.issues)
        issue_lines = [
            (
                f"- [{issue.severity}] {issue.title} | "
                f"{issue.workstream_domain} | {issue.status}\n"
                f"  Impact: {issue.business_impact}\n"
                f"  Action: {issue.recommended_action or 'Triage pending'}"
            )
            for issue in sorted_issues
        ] or ["- No issues have been registered."]

        return "\n".join(
            [
                f"# Issue Register: {case.name}",
                "",
                f"Target: {case.target_name}",
                "",
                "## Issues",
                *issue_lines,
            ]
        )

    def _sorted_issues(self, issues):
        return sorted(
            issues,
            key=lambda issue: (
                SEVERITY_ORDER.get(issue.severity, 99),
                issue.created_at,
            ),
        )

    def _build_next_actions(
        self,
        motion_pack: MotionPack,
        open_mandatory_items: int,
        issues,
        open_request_count: int,
        approval_state: ApprovalDecisionKind | None,
    ) -> list[str]:
        actions: list[str] = []
        review_label = (
            "credit committee review"
            if motion_pack == MotionPack.CREDIT_LENDING
            else "vendor approval"
            if motion_pack == MotionPack.VENDOR_ONBOARDING
            else "final review"
        )
        request_label = (
            "borrower information requests"
            if motion_pack == MotionPack.CREDIT_LENDING
            else "vendor follow-up requests and attestations"
            if motion_pack == MotionPack.VENDOR_ONBOARDING
            else "data-room requests and management responses"
        )
        if open_mandatory_items:
            actions.append(
                f"Close {open_mandatory_items} mandatory checklist items before {review_label}."
            )
        if issues:
            if motion_pack == MotionPack.CREDIT_LENDING:
                actions.append(
                    "Resolve, mitigate, or formally accept the highest-severity open credit risks."
                )
            elif motion_pack == MotionPack.VENDOR_ONBOARDING:
                actions.append(
                    "Resolve, mitigate, or escalate the highest-severity third-party risks."
                )
            else:
                actions.append("Resolve or formally accept the highest-severity open issues.")
        if open_request_count:
            actions.append(f"Chase outstanding {request_label}.")
        if approval_state != ApprovalDecisionKind.APPROVED:
            if motion_pack == MotionPack.CREDIT_LENDING:
                actions.append("Re-run credit approval after blockers are closed.")
            elif motion_pack == MotionPack.VENDOR_ONBOARDING:
                actions.append("Re-run vendor approval after blockers are closed.")
            else:
                actions.append("Re-run approval review after blockers are closed.")
        return actions[:4]

    def _build_summary(
        self,
        motion_pack: MotionPack,
        sector_pack: SectorPack,
        case_name: str,
        target_name: str,
        issue_count: int,
        open_mandatory_items: int,
        open_request_count: int,
        financial_summary,
        legal_summary,
        tax_summary,
        compliance_summary,
        commercial_summary,
        operations_summary,
        cyber_summary,
        forensic_summary,
        buy_side_analysis,
        borrower_scorecard,
        vendor_risk_tier,
        tech_saas_metrics,
        manufacturing_metrics,
        bfsi_nbfc_metrics,
    ) -> str:
        financial_note = ""
        if financial_summary is not None and financial_summary.periods:
            latest = financial_summary.periods[-1]
            fragments: list[str] = []
            if latest.revenue is not None:
                fragments.append(f"latest revenue {latest.revenue:.2f}")
            if latest.ebitda is not None:
                fragments.append(f"reported EBITDA {latest.ebitda:.2f}")
            if financial_summary.normalized_ebitda is not None:
                fragments.append(f"normalized EBITDA {financial_summary.normalized_ebitda:.2f}")
            if fragments:
                financial_note = " Financial QoE parsing extracted " + ", ".join(fragments) + "."

        compliance_fragments: list[str] = []
        if legal_summary is not None:
            if legal_summary.contract_reviews:
                compliance_fragments.append(
                    f"{len(legal_summary.contract_reviews)} contract reviews"
                )
            if legal_summary.flags:
                compliance_fragments.append(f"{len(legal_summary.flags)} legal governance flags")
        if tax_summary is not None:
            known_tax_items = [item for item in tax_summary.items if item.status.value != "unknown"]
            if known_tax_items:
                compliance_fragments.append(f"{len(known_tax_items)} tax areas with evidence")
        if compliance_summary is not None:
            known_matrix_items = [
                item for item in compliance_summary.items if item.status.value != "unknown"
            ]
            if known_matrix_items:
                compliance_fragments.append(
                    f"{len(known_matrix_items)} compliance-matrix items with determined status"
                )
        compliance_note = (
            ""
            if not compliance_fragments
            else " Phase 9 engines identified " + ", ".join(compliance_fragments) + "."
        )
        phase10_fragments: list[str] = []
        if commercial_summary is not None:
            if commercial_summary.concentration_signals:
                phase10_fragments.append(
                    f"{len(commercial_summary.concentration_signals)} commercial "
                    "concentration signals"
                )
            if commercial_summary.renewal_signals:
                phase10_fragments.append(
                    f"{len(commercial_summary.renewal_signals)} renewal signals"
                )
        if operations_summary is not None:
            if operations_summary.dependency_signals:
                phase10_fragments.append(
                    f"{len(operations_summary.dependency_signals)} operations dependency signals"
                )
        if cyber_summary is not None:
            known_controls = [
                item for item in cyber_summary.controls if item.status.value != "unknown"
            ]
            if known_controls:
                phase10_fragments.append(
                    f"{len(known_controls)} cyber/privacy controls with evidence"
                )
        if forensic_summary is not None and forensic_summary.flags:
            phase10_fragments.append(f"{len(forensic_summary.flags)} forensic red flags")
        phase10_note = (
            ""
            if not phase10_fragments
            else " Phase 10 engines identified " + ", ".join(phase10_fragments) + "."
        )
        phase11_note = ""
        if motion_pack == MotionPack.BUY_SIDE_DILIGENCE and buy_side_analysis is not None:
            phase11_note = (
                " Phase 11 buy-side deepening identified "
                f"{len(buy_side_analysis.valuation_bridge)} valuation bridge items, "
                f"{len(buy_side_analysis.spa_issues)} SPA issue clusters, and "
                f"{len(buy_side_analysis.pmi_risks)} PMI risks."
            )
        elif motion_pack == MotionPack.CREDIT_LENDING and borrower_scorecard is not None:
            phase11_note = (
                " Phase 11 credit deepening produced a borrower score of "
                f"{borrower_scorecard.overall_score}/100 with "
                f"{len(borrower_scorecard.covenant_tracking)} covenant tracking items."
            )
        elif motion_pack == MotionPack.VENDOR_ONBOARDING and vendor_risk_tier is not None:
            phase11_note = (
                " Phase 11 vendor deepening classified the vendor as "
                f"{vendor_risk_tier.tier} with score {vendor_risk_tier.overall_score}/100 and "
                f"{len(vendor_risk_tier.certifications_required)} outstanding certification asks."
            )

        phase12_note = ""
        if sector_pack == SectorPack.TECH_SAAS_SERVICES and tech_saas_metrics is not None:
            fragments: list[str] = []
            if tech_saas_metrics.arr is not None:
                fragments.append(f"ARR {tech_saas_metrics.arr:.2f}")
            if tech_saas_metrics.nrr is not None:
                fragments.append(f"NRR {tech_saas_metrics.nrr:.0%}")
            if tech_saas_metrics.payback_months is not None:
                fragments.append(f"CAC payback {tech_saas_metrics.payback_months:.1f} months")
            if fragments:
                phase12_note = (
                    " Phase 12 Tech/SaaS deepening extracted "
                    + ", ".join(fragments)
                    + "."
                )
            if tech_saas_metrics.flags:
                phase12_note += " Flags: " + "; ".join(tech_saas_metrics.flags[:2]) + "."
        elif (
            sector_pack == SectorPack.MANUFACTURING_INDUSTRIALS
            and manufacturing_metrics is not None
        ):
            fragments = []
            if manufacturing_metrics.capacity_utilization is not None:
                fragments.append(
                    f"capacity utilization {manufacturing_metrics.capacity_utilization:.0%}"
                )
            if manufacturing_metrics.dio is not None:
                fragments.append(f"DIO {manufacturing_metrics.dio:.0f} days")
            if manufacturing_metrics.asset_turnover is not None:
                fragments.append(f"asset turnover {manufacturing_metrics.asset_turnover:.2f}x")
            if fragments:
                phase12_note = (
                    " Phase 12 Manufacturing deepening extracted " + ", ".join(fragments) + "."
                )
            if manufacturing_metrics.flags:
                phase12_note += " Flags: " + "; ".join(manufacturing_metrics.flags[:2]) + "."
        elif sector_pack == SectorPack.BFSI_NBFC and bfsi_nbfc_metrics is not None:
            fragments = []
            if bfsi_nbfc_metrics.gnpa is not None:
                fragments.append(f"GNPA {bfsi_nbfc_metrics.gnpa:.2%}")
            if bfsi_nbfc_metrics.crar is not None:
                fragments.append(f"CRAR {bfsi_nbfc_metrics.crar:.2%}")
            if bfsi_nbfc_metrics.alm_mismatch is not None:
                fragments.append(f"ALM mismatch {bfsi_nbfc_metrics.alm_mismatch:.2%}")
            if fragments:
                phase12_note = (
                    " Phase 12 BFSI/NBFC deepening extracted "
                    + ", ".join(fragments)
                    + "."
                )
            if bfsi_nbfc_metrics.flags:
                phase12_note += " Flags: " + "; ".join(bfsi_nbfc_metrics.flags[:2]) + "."

        if motion_pack == MotionPack.CREDIT_LENDING:
            return (
                f"{case_name} for {target_name} currently has {issue_count} tracked credit-risk "
                f"items, {open_mandatory_items} open mandatory underwriting checklist items, "
                f"and {open_request_count} open borrower information requests."
                f"{financial_note}{compliance_note}{phase10_note}{phase11_note}{phase12_note}"
            )
        if motion_pack == MotionPack.VENDOR_ONBOARDING:
            return (
                f"{case_name} for {target_name} currently has {issue_count} tracked "
                f"third-party risk items, {open_mandatory_items} open mandatory onboarding "
                f"checklist items, and {open_request_count} open vendor follow-up requests."
                f"{financial_note}{compliance_note}{phase10_note}{phase11_note}{phase12_note}"
            )
        return (
            f"{case_name} for {target_name} currently has {issue_count} tracked issues, "
            f"{open_mandatory_items} open mandatory checklist items, and "
            f"{open_request_count} open diligence requests."
            f"{financial_note}{compliance_note}{phase10_note}{phase11_note}{phase12_note}"
        )

    def _build_motion_pack_highlights(
        self,
        motion_pack: MotionPack,
        buy_side_analysis,
        borrower_scorecard,
        vendor_risk_tier,
    ) -> list[str]:
        if motion_pack == MotionPack.BUY_SIDE_DILIGENCE and buy_side_analysis is not None:
            highlights: list[str] = []
            if buy_side_analysis.valuation_bridge:
                highlights.append(
                    f"{len(buy_side_analysis.valuation_bridge)} valuation bridge "
                    "items are ready for IC review."
                )
            if buy_side_analysis.spa_issues:
                highlights.append(
                    f"{len(buy_side_analysis.spa_issues)} SPA issue clusters "
                    "should be translated into deal protections."
                )
            if buy_side_analysis.pmi_risks:
                highlights.append(
                    f"{len(buy_side_analysis.pmi_risks)} PMI risks should be "
                    "assigned into Day 1 / Day 100 planning."
                )
            return highlights[:4]
        if motion_pack == MotionPack.CREDIT_LENDING and borrower_scorecard is not None:
            return [
                "Borrower scorecard: "
                f"{borrower_scorecard.overall_score}/100 "
                f"({borrower_scorecard.overall_rating}).",
                f"Financial health score: {borrower_scorecard.financial_health.score}/100.",
                f"Collateral score: {borrower_scorecard.collateral.score}/100.",
                f"Covenant tracking items: {len(borrower_scorecard.covenant_tracking)}.",
            ]
        if motion_pack == MotionPack.VENDOR_ONBOARDING and vendor_risk_tier is not None:
            return [
                f"Vendor tier: {vendor_risk_tier.tier}.",
                f"Overall vendor score: {vendor_risk_tier.overall_score}/100.",
                f"Questionnaire sections assessed: {len(vendor_risk_tier.questionnaire)}.",
                (
                    "Outstanding certifications: "
                    + (", ".join(vendor_risk_tier.certifications_required) or "none")
                    + "."
                ),
            ]
        return []

    def _build_sector_pack_highlights(
        self,
        sector_pack: SectorPack,
        tech_saas_metrics,
        manufacturing_metrics,
        bfsi_nbfc_metrics,
    ) -> list[str]:
        if sector_pack == SectorPack.TECH_SAAS_SERVICES and tech_saas_metrics is not None:
            highlights: list[str] = []
            if tech_saas_metrics.arr is not None:
                highlights.append(f"ARR tracked at {tech_saas_metrics.arr:.2f}.")
            if tech_saas_metrics.nrr is not None:
                highlights.append(f"NRR tracked at {tech_saas_metrics.nrr:.0%}.")
            if tech_saas_metrics.churn_rate is not None:
                highlights.append(f"Churn tracked at {tech_saas_metrics.churn_rate:.0%}.")
            if tech_saas_metrics.payback_months is not None:
                highlights.append(
                    f"CAC payback tracked at {tech_saas_metrics.payback_months:.1f} months."
                )
            return (highlights or tech_saas_metrics.flags[:4])[:4]
        if (
            sector_pack == SectorPack.MANUFACTURING_INDUSTRIALS
            and manufacturing_metrics is not None
        ):
            highlights = []
            if manufacturing_metrics.capacity_utilization is not None:
                highlights.append(
                    "Capacity utilization: "
                    f"{manufacturing_metrics.capacity_utilization:.0%}."
                )
            if manufacturing_metrics.dio is not None:
                highlights.append(f"Inventory days: {manufacturing_metrics.dio:.0f}.")
            if manufacturing_metrics.asset_register:
                highlights.append(
                    f"Asset register findings: {len(manufacturing_metrics.asset_register)}."
                )
            return (highlights or manufacturing_metrics.flags[:4])[:4]
        if sector_pack == SectorPack.BFSI_NBFC and bfsi_nbfc_metrics is not None:
            highlights = []
            if bfsi_nbfc_metrics.gnpa is not None:
                highlights.append(f"GNPA: {bfsi_nbfc_metrics.gnpa:.2%}.")
            if bfsi_nbfc_metrics.nnpa is not None:
                highlights.append(f"NNPA: {bfsi_nbfc_metrics.nnpa:.2%}.")
            if bfsi_nbfc_metrics.crar is not None:
                highlights.append(f"CRAR: {bfsi_nbfc_metrics.crar:.2%}.")
            if bfsi_nbfc_metrics.psl_compliance != ComplianceStatus.UNKNOWN:
                highlights.append(
                    "PSL compliance: "
                    f"{bfsi_nbfc_metrics.psl_compliance.value.replace('_', ' ')}."
                )
            return (highlights or bfsi_nbfc_metrics.flags[:4])[:4]
        return []

    def _report_title_for_motion(self, motion_pack: MotionPack) -> str:
        if motion_pack == MotionPack.CREDIT_LENDING:
            return "Credit Memo"
        if motion_pack == MotionPack.VENDOR_ONBOARDING:
            return "Third-Party Risk Memo"
        return "Executive Memo"
