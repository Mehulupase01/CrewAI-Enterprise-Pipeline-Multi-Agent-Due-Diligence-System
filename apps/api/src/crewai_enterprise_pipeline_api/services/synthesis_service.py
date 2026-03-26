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
    def build_workstream_syntheses(self, case, run_id: str) -> list[WorkstreamSynthesisRecord]:
        syntheses: list[WorkstreamSynthesisRecord] = []
        for workstream in WorkstreamDomain:
            scoped_checklist = [
                item
                for item in case.checklist_items
                if item.workstream_domain == workstream.value
            ]
            scoped_evidence = [
                item
                for item in case.evidence_items
                if item.workstream_domain == workstream.value
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
                item
                for item in scoped_issues
                if item.severity in BLOCKING_SEVERITIES
            ]

            blocker_count = (
                len(blocking_issues) + len(blocked_checklist) + len(open_mandatory)
            )
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
                f" Highest-priority concern: {top_issue.title}. "
                f"Impact: {top_issue.business_impact}"
            )

        return (
            f"{self._label_for_domain(workstream.value)} synthesis: {evidence_note} {issue_note}. "
            f"{checklist_note}{top_issue_note}"
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
