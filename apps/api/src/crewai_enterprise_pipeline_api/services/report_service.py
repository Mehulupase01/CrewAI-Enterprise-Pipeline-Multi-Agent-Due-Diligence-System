from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.domain.models import (
    ApprovalDecisionKind,
    ExecutiveMemoReport,
    FlagSeverity,
)
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.services.checklist_service import ChecklistService

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
        self.case_service = CaseService(session)
        self.checklist_service = ChecklistService(session)

    async def build_executive_memo(self, case_id: str) -> ExecutiveMemoReport | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        coverage = await self.checklist_service.get_coverage_summary(case_id)
        if coverage is None:
            return None

        sorted_issues = self._sorted_issues(case.issues)
        latest_approval = case.approvals[-1] if case.approvals else None
        approval_state = None if latest_approval is None else ApprovalDecisionKind(
            latest_approval.decision
        )
        report_status = (
            "ready_for_export"
            if latest_approval is not None and latest_approval.ready_for_export
            else "not_ready"
        )
        open_requests = [
            request for request in case.request_items if request.status != "closed"
        ]

        executive_summary = (
            f"{case.name} for {case.target_name} currently has {len(sorted_issues)} "
            f"tracked issues, {coverage.open_mandatory_items} open mandatory checklist "
            f"items, and {len(open_requests)} open diligence requests."
        )
        next_actions = self._build_next_actions(
            coverage.open_mandatory_items,
            sorted_issues,
            len(open_requests),
            approval_state,
        )

        return ExecutiveMemoReport(
            case_id=case.id,
            case_name=case.name,
            target_name=case.target_name,
            generated_at=datetime.now(UTC),
            report_status=report_status,
            approval_state=approval_state,
            executive_summary=executive_summary,
            top_issues=sorted_issues[:5],
            open_requests=open_requests[:5],
            checklist_coverage=coverage,
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
            f"- {request.title} ({request.status})"
            for request in memo.open_requests
        ] or ["- No open diligence requests."]
        next_action_lines = [
            f"- {action}" for action in memo.next_actions
        ] or ["- No immediate next actions recorded."]

        return "\n".join(
            [
                f"# Executive Memo: {memo.case_name}",
                "",
                f"Target: {memo.target_name}",
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
                (
                    f"- Mandatory open items: "
                    f"{memo.checklist_coverage.open_mandatory_items}"
                ),
                f"- Completion ready: {memo.checklist_coverage.completion_ready}",
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
        open_mandatory_items: int,
        issues,
        open_request_count: int,
        approval_state: ApprovalDecisionKind | None,
    ) -> list[str]:
        actions: list[str] = []
        if open_mandatory_items:
            actions.append(
                f"Close {open_mandatory_items} mandatory checklist items before final review."
            )
        if issues:
            actions.append("Resolve or formally accept the highest-severity open issues.")
        if open_request_count:
            actions.append("Chase outstanding data-room requests and management responses.")
        if approval_state != ApprovalDecisionKind.APPROVED:
            actions.append("Re-run approval review after blockers are closed.")
        return actions[:4]
