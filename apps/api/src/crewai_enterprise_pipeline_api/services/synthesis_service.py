from __future__ import annotations

from crewai_enterprise_pipeline_api.db.models import WorkstreamSynthesisRecord
from crewai_enterprise_pipeline_api.domain.models import (
    ChecklistItemStatus,
    FlagSeverity,
    IssueStatus,
    WorkstreamDomain,
    WorkstreamSynthesisStatus,
)

ACTIVE_ISSUE_STATUSES = {
    IssueStatus.OPEN.value,
    IssueStatus.IN_REVIEW.value,
    IssueStatus.MITIGATION_PLANNED.value,
}

BLOCKING_SEVERITIES = {
    FlagSeverity.CRITICAL.value,
    FlagSeverity.HIGH.value,
}

COMPLETED_CHECKLIST_STATUSES = {
    ChecklistItemStatus.SATISFIED.value,
    ChecklistItemStatus.NOT_APPLICABLE.value,
}


class SynthesisService:
    def build_workstream_syntheses(
        self,
        case,
        run_id: str,
        financial_summary=None,
        legal_summary=None,
        tax_summary=None,
        compliance_summary=None,
        commercial_summary=None,
        operations_summary=None,
        cyber_summary=None,
        forensic_summary=None,
        buy_side_analysis=None,
        borrower_scorecard=None,
        vendor_risk_tier=None,
        tech_saas_metrics=None,
        manufacturing_metrics=None,
        bfsi_nbfc_metrics=None,
    ) -> list[WorkstreamSynthesisRecord]:
        syntheses: list[WorkstreamSynthesisRecord] = []
        for workstream in WorkstreamDomain:
            scoped_checklist = [
                item for item in case.checklist_items if item.workstream_domain == workstream.value
            ]
            scoped_evidence = [
                item for item in case.evidence_items if item.workstream_domain == workstream.value
            ]
            scoped_issues = [
                item
                for item in case.issues
                if item.workstream_domain == workstream.value
                and item.status in ACTIVE_ISSUE_STATUSES
            ]

            if not (scoped_checklist or scoped_evidence or scoped_issues):
                continue

            open_mandatory = [
                item
                for item in scoped_checklist
                if item.mandatory and item.status not in COMPLETED_CHECKLIST_STATUSES
            ]
            blocked_checklist = [
                item
                for item in scoped_checklist
                if item.status == ChecklistItemStatus.BLOCKED.value
            ]
            blocking_issues = [
                item for item in scoped_issues if item.severity in BLOCKING_SEVERITIES
            ]

            blocker_count = len(blocking_issues) + len(blocked_checklist) + len(open_mandatory)
            if blocking_issues or blocked_checklist:
                status = WorkstreamSynthesisStatus.BLOCKED
            elif open_mandatory or scoped_issues:
                status = WorkstreamSynthesisStatus.NEEDS_FOLLOW_UP
            else:
                status = WorkstreamSynthesisStatus.READY_FOR_REVIEW

            headline = self._build_headline(workstream, status, blocker_count)
            narrative = self._build_narrative(
                workstream,
                scoped_evidence,
                scoped_issues,
                open_mandatory,
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
            recommended_next_action = self._build_next_action(
                scoped_issues,
                open_mandatory,
                scoped_checklist,
            )
            finding_count = len(scoped_evidence) + len(scoped_issues)
            confidence = min(
                0.55 + (0.1 * min(len(scoped_evidence), 3)) + (0.05 * min(len(scoped_issues), 3)),
                0.95,
            )

            syntheses.append(
                WorkstreamSynthesisRecord(
                    case_id=case.id,
                    run_id=run_id,
                    workstream_domain=workstream.value,
                    status=status.value,
                    headline=headline,
                    narrative=narrative,
                    finding_count=finding_count,
                    blocker_count=blocker_count,
                    confidence=confidence,
                    recommended_next_action=recommended_next_action,
                )
            )

        return syntheses

    def render_markdown(self, case, syntheses: list[WorkstreamSynthesisRecord]) -> str:
        sections: list[str] = [
            f"# Workstream Syntheses: {case.name}",
            "",
            f"Target: {case.target_name}",
            "",
        ]
        if not syntheses:
            sections.extend(["No workstream syntheses were generated.", ""])
            return "\n".join(sections)

        for synthesis in syntheses:
            sections.extend(
                [
                    f"## {self._label_for_domain(synthesis.workstream_domain)}",
                    f"Status: {synthesis.status}",
                    f"Headline: {synthesis.headline}",
                    "",
                    synthesis.narrative,
                    "",
                    f"Findings: {synthesis.finding_count}",
                    f"Blockers: {synthesis.blocker_count}",
                    f"Confidence: {synthesis.confidence:.2f}",
                    f"Next action: {synthesis.recommended_next_action}",
                    "",
                ]
            )
        return "\n".join(sections)

    def _build_headline(
        self,
        workstream: WorkstreamDomain,
        status: WorkstreamSynthesisStatus,
        blocker_count: int,
    ) -> str:
        label = self._label_for_domain(workstream.value)
        if status == WorkstreamSynthesisStatus.BLOCKED:
            return f"{label} is blocked by {blocker_count} unresolved items."
        if status == WorkstreamSynthesisStatus.NEEDS_FOLLOW_UP:
            return f"{label} needs follow-up before sign-off."
        return f"{label} is currently ready for reviewer assessment."

    def _build_narrative(
        self,
        workstream: WorkstreamDomain,
        scoped_evidence,
        scoped_issues,
        open_mandatory,
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
        evidence_note = (
            f"The evidence ledger includes {len(scoped_evidence)} items"
            if scoped_evidence
            else "No direct evidence has been logged yet"
        )
        issue_note = (
            f"with {len(scoped_issues)} active issues under this workstream"
            if scoped_issues
            else "and no active issue-register entries in this lane"
        )
        checklist_note = (
            f"{len(open_mandatory)} mandatory checklist items still need completion."
            if open_mandatory
            else "All mandatory checklist items in this lane are closed or not applicable."
        )

        top_issue_note = ""
        if scoped_issues:
            top_issue = sorted(
                scoped_issues,
                key=lambda issue: self._severity_rank(issue.severity),
            )[0]
            top_issue_note = (
                f" Highest-priority concern: {top_issue.title}. Impact: {top_issue.business_impact}"
            )

        financial_note = ""
        if (
            workstream == WorkstreamDomain.FINANCIAL_QOE
            and financial_summary is not None
            and financial_summary.periods
        ):
            latest = financial_summary.periods[-1]
            metrics: list[str] = []
            if latest.revenue is not None:
                metrics.append(f"latest revenue {latest.revenue:.2f}")
            if latest.ebitda is not None:
                metrics.append(f"reported EBITDA {latest.ebitda:.2f}")
            if financial_summary.normalized_ebitda is not None:
                metrics.append(f"normalized EBITDA {financial_summary.normalized_ebitda:.2f}")
            if metrics:
                financial_note = " Parsed financial package shows " + ", ".join(metrics) + "."
            if financial_summary.flags:
                financial_note += " Flags: " + "; ".join(financial_summary.flags[:3]) + "."

        phase9_note = ""
        if workstream == WorkstreamDomain.LEGAL_CORPORATE and legal_summary is not None:
            phase9_note = (
                " Structured legal analysis identified "
                f"{len(legal_summary.directors)} directors, "
                f"{len(legal_summary.contract_reviews)} contract reviews, and "
                f"{legal_summary.charges_detected} charge references."
            )
            if legal_summary.flags:
                phase9_note += " Flags: " + "; ".join(legal_summary.flags[:3]) + "."
        elif workstream == WorkstreamDomain.TAX and tax_summary is not None:
            known_tax_items = [item for item in tax_summary.items if item.status.value != "unknown"]
            phase9_note = (
                " Structured tax analysis identified "
                f"{len(known_tax_items)} tax areas with evidence and "
                f"{len(tax_summary.gstins)} GSTIN references."
            )
            if tax_summary.flags:
                phase9_note += " Flags: " + "; ".join(tax_summary.flags[:3]) + "."
        elif workstream == WorkstreamDomain.REGULATORY and compliance_summary is not None:
            known_matrix_items = [
                item for item in compliance_summary.items if item.status.value != "unknown"
            ]
            phase9_note = (
                " Compliance matrix generated "
                f"{len(compliance_summary.items)} items with "
                f"{len(known_matrix_items)} determined statuses."
            )
            if compliance_summary.flags:
                phase9_note += " Flags: " + "; ".join(compliance_summary.flags[:3]) + "."
        elif workstream == WorkstreamDomain.COMMERCIAL and commercial_summary is not None:
            phase9_note = (
                " Structured commercial analysis identified "
                f"{len(commercial_summary.concentration_signals)} concentration signals and "
                f"{len(commercial_summary.renewal_signals)} renewal signals."
            )
            if commercial_summary.net_revenue_retention is not None:
                phase9_note += f" NRR: {commercial_summary.net_revenue_retention:.0%}."
            if commercial_summary.churn_rate is not None:
                phase9_note += f" Churn: {commercial_summary.churn_rate:.0%}."
            if commercial_summary.flags:
                phase9_note += " Flags: " + "; ".join(commercial_summary.flags[:3]) + "."
        elif workstream == WorkstreamDomain.OPERATIONS and operations_summary is not None:
            phase9_note = (
                " Structured operations analysis identified "
                f"{len(operations_summary.dependency_signals)} dependency signals."
            )
            if operations_summary.supplier_concentration_top_3 is not None:
                phase9_note += (
                    " Supplier concentration: "
                    f"{operations_summary.supplier_concentration_top_3:.0%}."
                )
            if operations_summary.flags:
                phase9_note += " Flags: " + "; ".join(operations_summary.flags[:3]) + "."
        elif workstream == WorkstreamDomain.CYBER_PRIVACY and cyber_summary is not None:
            known_controls = [
                item for item in cyber_summary.controls if item.status.value != "unknown"
            ]
            phase9_note = (
                " Structured cyber/privacy analysis identified "
                f"{len(known_controls)} controls with evidence and "
                f"{len(cyber_summary.certifications)} certification signals."
            )
            if cyber_summary.breach_history:
                phase9_note += f" Breach signals: {len(cyber_summary.breach_history)}."
            if cyber_summary.flags:
                phase9_note += " Flags: " + "; ".join(cyber_summary.flags[:3]) + "."
        elif workstream == WorkstreamDomain.FORENSIC_COMPLIANCE and forensic_summary is not None:
            phase9_note = (
                f" Structured forensic analysis identified {len(forensic_summary.flags)} red flags."
            )
            if forensic_summary.flags:
                phase9_note += (
                    " Flag types: "
                    + ", ".join(flag.flag_type.value for flag in forensic_summary.flags[:4])
                    + "."
                )

        phase11_note = ""
        if workstream == WorkstreamDomain.FINANCIAL_QOE:
            if buy_side_analysis is not None:
                phase11_note = (
                    " Phase 11 buy-side deepening translated the financial lane into "
                    f"{len(buy_side_analysis.valuation_bridge)} valuation bridge items."
                )
            elif borrower_scorecard is not None:
                phase11_note = (
                    " Phase 11 credit deepening scored financial health at "
                    f"{borrower_scorecard.financial_health.score}/100."
                )
            elif vendor_risk_tier is not None:
                financial_resilience_score = next(
                    (
                        item.score
                        for item in vendor_risk_tier.scoring_breakdown
                        if item.factor == "financial_resilience"
                    ),
                    0,
                )
                phase11_note = (
                    " Phase 11 vendor deepening scored financial resilience at "
                    f"{financial_resilience_score}/100."
                )
        elif workstream == WorkstreamDomain.LEGAL_CORPORATE and buy_side_analysis is not None:
            phase11_note = (
                " Phase 11 buy-side deepening translated legal findings into "
                f"{len(buy_side_analysis.spa_issues)} SPA issue clusters."
            )
        elif workstream == WorkstreamDomain.REGULATORY and vendor_risk_tier is not None:
            phase11_note = (
                f" Phase 11 vendor deepening classified the vendor as {vendor_risk_tier.tier}."
            )
        elif workstream == WorkstreamDomain.CYBER_PRIVACY and vendor_risk_tier is not None:
            phase11_note = (
                " Phase 11 vendor deepening identified "
                f"{len(vendor_risk_tier.certifications_required)} outstanding certification asks."
            )
        elif workstream == WorkstreamDomain.OPERATIONS and buy_side_analysis is not None:
            phase11_note = (
                " Phase 11 buy-side deepening produced "
                f"{len(buy_side_analysis.pmi_risks)} PMI readiness items."
            )

        phase12_note = ""
        if workstream == WorkstreamDomain.COMMERCIAL and tech_saas_metrics is not None:
            fragments = []
            if tech_saas_metrics.arr is not None:
                fragments.append(f"ARR {tech_saas_metrics.arr:.2f}")
            if tech_saas_metrics.nrr is not None:
                fragments.append(f"NRR {tech_saas_metrics.nrr:.0%}")
            if tech_saas_metrics.churn_rate is not None:
                fragments.append(f"churn {tech_saas_metrics.churn_rate:.0%}")
            if fragments:
                phase12_note = (
                    " Phase 12 Tech/SaaS deepening extracted " + ", ".join(fragments) + "."
                )
        elif workstream == WorkstreamDomain.OPERATIONS and tech_saas_metrics is not None:
            if tech_saas_metrics.payback_months is not None:
                phase12_note = (
                    " Phase 12 Tech/SaaS deepening captured CAC payback at "
                    f"{tech_saas_metrics.payback_months:.1f} months alongside delivery risk."
                )
        elif workstream == WorkstreamDomain.CYBER_PRIVACY and tech_saas_metrics is not None:
            if any("SOC 2" in flag for flag in tech_saas_metrics.flags):
                phase12_note = " Phase 12 Tech/SaaS deepening flagged SaaS-grade assurance gaps."
        elif workstream == WorkstreamDomain.OPERATIONS and manufacturing_metrics is not None:
            fragments = []
            if manufacturing_metrics.capacity_utilization is not None:
                fragments.append(
                    f"capacity utilization {manufacturing_metrics.capacity_utilization:.0%}"
                )
            if manufacturing_metrics.dio is not None:
                fragments.append(f"DIO {manufacturing_metrics.dio:.0f} days")
            if fragments:
                phase12_note = (
                    " Phase 12 Manufacturing deepening extracted " + ", ".join(fragments) + "."
                )
        elif workstream == WorkstreamDomain.FINANCIAL_QOE and manufacturing_metrics is not None:
            if manufacturing_metrics.asset_turnover is not None:
                phase12_note = (
                    " Phase 12 Manufacturing deepening captured asset turnover at "
                    f"{manufacturing_metrics.asset_turnover:.2f}x."
                )
        elif workstream == WorkstreamDomain.REGULATORY and manufacturing_metrics is not None:
            if any("EHS" in flag or "factory" in flag for flag in manufacturing_metrics.flags):
                phase12_note = (
                    " Phase 12 Manufacturing deepening surfaced EHS/factory compliance gaps."
                )
        elif (
            workstream == WorkstreamDomain.FORENSIC_COMPLIANCE
            and manufacturing_metrics is not None
        ):
            if any(
                "integrity" in flag.lower() or "procurement" in flag.lower()
                for flag in manufacturing_metrics.flags
            ):
                phase12_note = (
                    " Phase 12 Manufacturing deepening highlighted "
                    "procurement integrity review needs."
                )
        elif workstream == WorkstreamDomain.FINANCIAL_QOE and bfsi_nbfc_metrics is not None:
            fragments = []
            if bfsi_nbfc_metrics.gnpa is not None:
                fragments.append(f"GNPA {bfsi_nbfc_metrics.gnpa:.2%}")
            if bfsi_nbfc_metrics.crar is not None:
                fragments.append(f"CRAR {bfsi_nbfc_metrics.crar:.2%}")
            if bfsi_nbfc_metrics.alm_mismatch is not None:
                fragments.append(f"ALM mismatch {bfsi_nbfc_metrics.alm_mismatch:.2%}")
            if fragments:
                phase12_note = (
                    " Phase 12 BFSI/NBFC deepening extracted " + ", ".join(fragments) + "."
                )
        elif workstream == WorkstreamDomain.REGULATORY and bfsi_nbfc_metrics is not None:
            if bfsi_nbfc_metrics.psl_compliance.value != "unknown":
                phase12_note = (
                    " Phase 12 BFSI/NBFC deepening recorded PSL posture as "
                    f"{bfsi_nbfc_metrics.psl_compliance.value.replace('_', ' ')}."
                )
        elif workstream == WorkstreamDomain.CYBER_PRIVACY and bfsi_nbfc_metrics is not None:
            if any("KYC" in flag or "borrower-data" in flag for flag in bfsi_nbfc_metrics.flags):
                phase12_note = (
                    " Phase 12 BFSI/NBFC deepening highlighted KYC/AML data-control gaps."
                )
        elif workstream == WorkstreamDomain.FORENSIC_COMPLIANCE and bfsi_nbfc_metrics is not None:
            if any(
                "connected lending" in flag.lower() or "evergreening" in flag.lower()
                for flag in bfsi_nbfc_metrics.flags
            ):
                phase12_note = (
                    " Phase 12 BFSI/NBFC deepening surfaced connected-lending "
                    "and evergreening concerns."
                )

        return (
            f"{self._label_for_domain(workstream.value)} synthesis: {evidence_note} {issue_note}. "
            f"{checklist_note}{top_issue_note}{financial_note}{phase9_note}{phase11_note}{phase12_note}"
        )

    def _build_next_action(
        self,
        scoped_issues,
        open_mandatory,
        scoped_checklist,
    ) -> str:
        if scoped_issues:
            top_issue = sorted(
                scoped_issues,
                key=lambda issue: self._severity_rank(issue.severity),
            )[0]
            if top_issue.recommended_action:
                return top_issue.recommended_action
            return f"Resolve the issue titled '{top_issue.title}' before review."
        if open_mandatory:
            return open_mandatory[0].detail
        if scoped_checklist:
            return "Maintain reviewer monitoring and keep supporting evidence current."
        return "No further action recorded."

    def _label_for_domain(self, workstream_domain: str) -> str:
        return workstream_domain.replace("_", " ").title()

    def _severity_rank(self, severity: str) -> int:
        ordering = {
            FlagSeverity.CRITICAL.value: 0,
            FlagSeverity.HIGH.value: 1,
            FlagSeverity.MEDIUM.value: 2,
            FlagSeverity.LOW.value: 3,
            FlagSeverity.INFO.value: 4,
        }
        return ordering.get(severity, 99)
