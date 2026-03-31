from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.domain.models import (
    BuySideAnalysis,
    ChecklistAutoUpdate,
    ChecklistItemStatus,
    ComplianceStatus,
    FlagSeverity,
    PmiRiskItem,
    SpaIssueItem,
    ValuationBridgeItem,
)
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.services.commercial_service import CommercialService
from crewai_enterprise_pipeline_api.services.cyber_service import CyberService
from crewai_enterprise_pipeline_api.services.financial_qoe_service import FinancialQoEService
from crewai_enterprise_pipeline_api.services.forensic_service import ForensicService
from crewai_enterprise_pipeline_api.services.legal_service import LegalService
from crewai_enterprise_pipeline_api.services.operations_service import OperationsService
from crewai_enterprise_pipeline_api.services.regulatory_service import RegulatoryService
from crewai_enterprise_pipeline_api.services.tax_service import TaxService

COMPLETED_CHECKLIST_STATUSES = {
    ChecklistItemStatus.SATISFIED.value,
    ChecklistItemStatus.NOT_APPLICABLE.value,
}


class BuySideService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)
        self.commercial_service = CommercialService(session)
        self.cyber_service = CyberService(session)
        self.financial_service = FinancialQoEService(session)
        self.forensic_service = ForensicService(session)
        self.legal_service = LegalService(session)
        self.operations_service = OperationsService(session)
        self.regulatory_service = RegulatoryService(session)
        self.tax_service = TaxService(session)

    async def build_buy_side_analysis(
        self,
        case_id: str,
        *,
        persist_checklist: bool = True,
    ) -> BuySideAnalysis | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        financial_summary = await self.financial_service.build_financial_summary(
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

        valuation_bridge = self._build_valuation_bridge(
            financial_summary,
            tax_summary,
            commercial_summary,
            case.issues,
        )
        spa_issues = self._build_spa_issues(
            case,
            legal_summary,
            tax_summary,
            compliance_summary,
            forensic_summary,
        )
        pmi_risks = self._build_pmi_risks(
            commercial_summary,
            operations_summary,
            cyber_summary,
            case.request_items,
        )
        flags = self._build_flags(valuation_bridge, spa_issues, pmi_risks)

        summary = BuySideAnalysis(
            case_id=case_id,
            valuation_bridge=valuation_bridge,
            spa_issues=spa_issues,
            pmi_risks=pmi_risks,
            flags=flags,
        )
        if persist_checklist:
            summary.checklist_updates = await self._auto_update_checklist(case, summary)
        return summary

    def _build_valuation_bridge(
        self,
        financial_summary,
        tax_summary,
        commercial_summary,
        issues,
    ) -> list[ValuationBridgeItem]:
        bridge: list[ValuationBridgeItem] = []
        statement_ids = []
        if financial_summary is not None:
            statement_ids = [
                statement.artifact_id
                for statement in financial_summary.statements
                if statement.artifact_id
            ]
            for adjustment in financial_summary.qoe_adjustments:
                bridge.append(
                    ValuationBridgeItem(
                        label=adjustment.label,
                        category=adjustment.category,
                        amount=round(-adjustment.amount, 4),
                        impact="QoE adjustment reflected in normalized EBITDA bridge.",
                        evidence_ids=statement_ids[:3],
                    )
                )
            latest = financial_summary.periods[-1] if financial_summary.periods else None
            if latest is not None and latest.net_debt is not None:
                bridge.append(
                    ValuationBridgeItem(
                        label="Net debt at closing",
                        category="net_debt",
                        amount=round(-latest.net_debt, 4),
                        impact="Net debt reduces equity value in the deal bridge.",
                        evidence_ids=statement_ids[:3],
                    )
                )
        if commercial_summary is not None and commercial_summary.concentration_signals:
            top_signal = commercial_summary.concentration_signals[0]
            bridge.append(
                ValuationBridgeItem(
                    label="Customer concentration valuation sensitivity",
                    category="commercial_risk",
                    amount=None,
                    impact=(
                        f"Top commercial concentration is {top_signal.share_of_revenue:.0%}; "
                        "valuation should reflect renewal and concentration downside."
                    ),
                    evidence_ids=top_signal.evidence_ids[:3],
                )
            )
        if tax_summary is not None and tax_summary.flags:
            bridge.append(
                ValuationBridgeItem(
                    label="Tax leakage reserve",
                    category="tax_exposure",
                    amount=None,
                    impact=(
                        "Open tax flags may require escrow, holdback, "
                        "or purchase-price protection."
                    ),
                    evidence_ids=[
                        evidence_id
                        for item in tax_summary.items
                        for evidence_id in item.evidence_ids[:1]
                    ][:3],
                )
            )
        for issue in issues:
            if issue.severity not in {FlagSeverity.HIGH.value, FlagSeverity.CRITICAL.value}:
                continue
            if issue.workstream_domain not in {"tax", "financial_qoe", "commercial"}:
                continue
            bridge.append(
                ValuationBridgeItem(
                    label=issue.title,
                    category="issue_register_adjustment",
                    amount=None,
                    impact=issue.business_impact,
                    evidence_ids=[issue.source_evidence_id] if issue.source_evidence_id else [],
                )
            )
        return bridge[:8]

    def _build_spa_issues(
        self,
        case,
        legal_summary,
        tax_summary,
        compliance_summary,
        forensic_summary,
    ) -> list[SpaIssueItem]:
        issues: list[SpaIssueItem] = []
        if legal_summary is not None and legal_summary.charges_detected:
            issues.append(
                SpaIssueItem(
                    title="Registered charges and encumbrances require closing treatment",
                    severity=FlagSeverity.HIGH,
                    rationale=(
                        "Legal review detected registered charges or encumbrances that should be "
                        "cleared, carved out, or addressed in closing deliverables."
                    ),
                    recommendation=(
                        "Add CPs for charge release or explicit debt/"
                        "refinancing treatment."
                    ),
                )
            )
        if legal_summary is not None:
            for review in legal_summary.contract_reviews:
                clause_keys = {clause.clause_key for clause in review.clauses if clause.present}
                if "change_of_control" in clause_keys:
                    issues.append(
                        SpaIssueItem(
                            title=f"Change-of-control consent risk in {review.contract_title}",
                            severity=FlagSeverity.HIGH,
                            rationale=(
                                "A material contract contains a change-of-control or consent "
                                "provision that could affect continuity post-closing."
                            ),
                            recommendation=(
                                "Track consent as a closing deliverable or "
                                "SPA condition precedent."
                            ),
                            evidence_ids=[review.artifact_id] if review.artifact_id else [],
                        )
                    )
                    break
        if tax_summary is not None and tax_summary.flags:
            issues.append(
                SpaIssueItem(
                    title="Tax indemnity and escrow sizing required",
                    severity=FlagSeverity.HIGH,
                    rationale=(
                        "Structured tax review surfaced flags that may require indemnity drafting, "
                        "specific disclosures, or tax escrow sizing."
                    ),
                    recommendation="Add targeted tax indemnities, disclosures, and escrow logic.",
                )
            )
        if compliance_summary is not None:
            problematic = [
                item
                for item in compliance_summary.items
                if item.status in {
                    ComplianceStatus.NON_COMPLIANT,
                    ComplianceStatus.PARTIALLY_COMPLIANT,
                }
            ]
            if problematic:
                issues.append(
                    SpaIssueItem(
                        title="Regulatory remediation items should become SPA conditions",
                        severity=FlagSeverity.HIGH,
                        rationale=(
                            f"{len(problematic)} regulatory items remain "
                            "non-compliant or partially "
                            "compliant in the structured matrix."
                        ),
                        recommendation=(
                            "Convert unresolved regulatory items into CPs, "
                            "covenants, or specific indemnities."
                        ),
                        evidence_ids=[
                            evidence_id
                            for item in problematic
                            for evidence_id in item.evidence_ids[:1]
                        ][:3],
                    )
                )
        if forensic_summary is not None and forensic_summary.flags:
            issues.append(
                SpaIssueItem(
                    title="Forensic bring-down and integrity protection required",
                    severity=FlagSeverity.CRITICAL,
                    rationale=(
                        "Structured forensic review surfaced integrity red flags that should be "
                        "reflected in bring-down conditions, disclosures, "
                        "and indemnity protections."
                    ),
                    recommendation=(
                        "Escalate to deal committee and hard-wire integrity "
                        "protections into SPA drafting."
                    ),
                    evidence_ids=[
                        evidence_id
                        for flag in forensic_summary.flags
                        for evidence_id in flag.evidence_ids[:1]
                    ][:3],
                )
            )
        for issue in case.issues:
            if issue.severity not in {FlagSeverity.HIGH.value, FlagSeverity.CRITICAL.value}:
                continue
            if issue.workstream_domain not in {
                "legal_corporate",
                "tax",
                "regulatory",
                "forensic_compliance",
            }:
                continue
            issues.append(
                SpaIssueItem(
                    title=issue.title,
                    severity=FlagSeverity(issue.severity),
                    rationale=issue.business_impact,
                    recommendation=(
                        issue.recommended_action
                        or "Escalate into SPA drafting and closing protections."
                    ),
                    evidence_ids=[issue.source_evidence_id] if issue.source_evidence_id else [],
                )
            )
        deduped: list[SpaIssueItem] = []
        seen: set[str] = set()
        for item in issues:
            key = item.title.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped[:8]

    def _build_pmi_risks(
        self,
        commercial_summary,
        operations_summary,
        cyber_summary,
        request_items,
    ) -> list[PmiRiskItem]:
        risks: list[PmiRiskItem] = []
        if operations_summary is not None and operations_summary.single_site_dependency:
            risks.append(
                PmiRiskItem(
                    area="Operations",
                    severity=FlagSeverity.HIGH,
                    description=(
                        "Single-site or continuity dependency may complicate "
                        "Day 1 operating resilience."
                    ),
                    day_one_action=(
                        "Prioritize continuity controls, alternate-site "
                        "planning, and owner mapping in the PMI plan."
                    ),
                )
            )
        if operations_summary is not None and operations_summary.key_person_dependencies:
            risks.append(
                PmiRiskItem(
                    area="People / Operations",
                    severity=FlagSeverity.HIGH,
                    description="Key-person dependence was detected in the operations review.",
                    day_one_action=(
                        "Create retention, backup-coverage, and transition "
                        "plans for named key operators."
                    ),
                )
            )
        if cyber_summary is not None:
            non_compliant_controls = [
                item
                for item in cyber_summary.controls
                if item.status in {
                    ComplianceStatus.NON_COMPLIANT,
                    ComplianceStatus.PARTIALLY_COMPLIANT,
                }
            ]
            if non_compliant_controls:
                risks.append(
                    PmiRiskItem(
                        area="Cyber / Privacy",
                        severity=FlagSeverity.HIGH,
                        description=(
                            "Material cyber or privacy controls remain "
                            "non-compliant or under remediation."
                        ),
                        day_one_action=(
                            "Stand up Day 1 access review, remediation "
                            "governance, and incident-response ownership."
                        ),
                        evidence_ids=[
                            evidence_id
                            for item in non_compliant_controls
                            for evidence_id in item.evidence_ids[:1]
                        ][:3],
                    )
                )
        if commercial_summary is not None and commercial_summary.concentration_signals:
            top_signal = commercial_summary.concentration_signals[0]
            if top_signal.share_of_revenue >= 0.35:
                risks.append(
                    PmiRiskItem(
                        area="Commercial",
                        severity=FlagSeverity.MEDIUM,
                        description=(
                            "Customer concentration remains elevated at "
                            f"{top_signal.share_of_revenue:.0%} "
                            "of revenue."
                        ),
                        day_one_action=(
                            "Track renewal and account-ownership transitions "
                            "in the Day 100 plan."
                        ),
                        evidence_ids=top_signal.evidence_ids[:3],
                    )
                )
        if any(item.status != "closed" for item in request_items):
            risks.append(
                PmiRiskItem(
                    area="Governance",
                    severity=FlagSeverity.MEDIUM,
                    description=(
                        "Open diligence requests remain unresolved at the "
                        "motion-pack level."
                    ),
                    day_one_action=(
                        "Convert unresolved diligence asks into Day 1 owners "
                        "and Day 30 remediation items."
                    ),
                )
            )
        return risks[:8]

    def _build_flags(
        self,
        valuation_bridge: list[ValuationBridgeItem],
        spa_issues: list[SpaIssueItem],
        pmi_risks: list[PmiRiskItem],
    ) -> list[str]:
        flags = []
        if valuation_bridge:
            flags.append(
                "Valuation bridge includes "
                f"{len(valuation_bridge)} adjustment or sensitivity items."
            )
        if spa_issues:
            flags.append(f"SPA drafting should reflect {len(spa_issues)} material issue clusters.")
        if pmi_risks:
            flags.append(
                f"PMI planning should address {len(pmi_risks)} Day 1 / Day 100 risk items."
            )
        return flags

    async def _auto_update_checklist(
        self, case, summary: BuySideAnalysis
    ) -> list[ChecklistAutoUpdate]:
        condition_map = {
            "financial_qoe.valuation_bridge": bool(summary.valuation_bridge),
            "legal_corporate.spa_issue_matrix": bool(summary.spa_issues),
            "operations.pmi_readiness_plan": bool(summary.pmi_risks),
            "commercial.revenue_quality_story": bool(summary.valuation_bridge),
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

    def _build_checklist_note(self, template_key: str, summary: BuySideAnalysis) -> str:
        if template_key == "financial_qoe.valuation_bridge":
            return (
                "Auto-satisfied by Phase 11 Buy-Side engine with "
                f"{len(summary.valuation_bridge)} valuation bridge items."
            )
        if template_key == "legal_corporate.spa_issue_matrix":
            return (
                "Auto-satisfied by Phase 11 Buy-Side engine with "
                f"{len(summary.spa_issues)} SPA issue clusters."
            )
        if template_key == "operations.pmi_readiness_plan":
            return (
                "Auto-satisfied by Phase 11 Buy-Side engine with "
                f"{len(summary.pmi_risks)} PMI readiness risks."
            )
        return "Auto-satisfied by Phase 11 Buy-Side engine."
