from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.domain.models import (
    ApprovalDecisionKind,
    ExecutiveMemoReport,
    FlagSeverity,
    MotionPack,
)
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.services.checklist_service import ChecklistService
from crewai_enterprise_pipeline_api.services.financial_qoe_service import FinancialQoEService

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
        self.financial_qoe_service = FinancialQoEService(session)

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
        motion_pack = MotionPack(case.motion_pack)
        report_title = self._report_title_for_motion(motion_pack)
        financial_summary = await self.financial_qoe_service.build_financial_summary(
            case_id,
            persist_checklist=False,
        )

        executive_summary = self._build_summary(
            motion_pack,
            case.name,
            case.target_name,
            len(sorted_issues),
            coverage.open_mandatory_items,
            len(open_requests),
            financial_summary,
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
            report_title=report_title,
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
                f"# {memo.report_title}: {memo.case_name}",
                "",
                f"Target: {memo.target_name}",
                f"Motion Pack: {memo.motion_pack.value}",
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
        case_name: str,
        target_name: str,
        issue_count: int,
        open_mandatory_items: int,
        open_request_count: int,
        financial_summary,
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
                fragments.append(
                    f"normalized EBITDA {financial_summary.normalized_ebitda:.2f}"
                )
            if fragments:
                financial_note = " Financial QoE parsing extracted " + ", ".join(fragments) + "."

        if motion_pack == MotionPack.CREDIT_LENDING:
            return (
                f"{case_name} for {target_name} currently has {issue_count} tracked credit-risk "
                f"items, {open_mandatory_items} open mandatory underwriting checklist items, "
                f"and {open_request_count} open borrower information requests."
                f"{financial_note}"
            )
        if motion_pack == MotionPack.VENDOR_ONBOARDING:
            return (
                f"{case_name} for {target_name} currently has {issue_count} tracked "
                f"third-party risk items, {open_mandatory_items} open mandatory onboarding "
                f"checklist items, and {open_request_count} open vendor follow-up requests."
                f"{financial_note}"
            )
        return (
            f"{case_name} for {target_name} currently has {issue_count} tracked issues, "
            f"{open_mandatory_items} open mandatory checklist items, and "
            f"{open_request_count} open diligence requests."
            f"{financial_note}"
        )

    def _report_title_for_motion(self, motion_pack: MotionPack) -> str:
        if motion_pack == MotionPack.CREDIT_LENDING:
            return "Credit Memo"
        if motion_pack == MotionPack.VENDOR_ONBOARDING:
            return "Third-Party Risk Memo"
        return "Executive Memo"
