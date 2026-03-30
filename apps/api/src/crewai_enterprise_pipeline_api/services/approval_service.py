from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.db.models import ApprovalDecisionRecord
from crewai_enterprise_pipeline_api.domain.models import (
    ApprovalDecisionCreate,
    ApprovalDecisionKind,
    ApprovalDecisionSummary,
    FlagSeverity,
    IssueStatus,
)
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.services.checklist_service import ChecklistService

ACTIVE_ISSUE_STATUSES = {
    IssueStatus.OPEN.value,
    IssueStatus.IN_REVIEW.value,
    IssueStatus.MITIGATION_PLANNED.value,
}

BLOCKING_SEVERITIES = {
    FlagSeverity.CRITICAL.value,
    FlagSeverity.HIGH.value,
}


class ApprovalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)
        self.checklist_service = ChecklistService(session)

    async def review_case(
        self,
        case_id: str,
        payload: ApprovalDecisionCreate,
    ) -> ApprovalDecisionSummary | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        coverage = await self.checklist_service.get_coverage_summary(case_id)
        if coverage is None:
            return None

        blocking_issue_count = sum(
            1
            for issue in case.issues
            if issue.status in ACTIVE_ISSUE_STATUSES
            and issue.severity in BLOCKING_SEVERITIES
        )
        ready_for_export = (
            coverage.completion_ready and blocking_issue_count == 0
        )
        if payload.decision is not None:
            decision = payload.decision.value
        else:
            decision = (
                ApprovalDecisionKind.APPROVED.value
                if ready_for_export
                else ApprovalDecisionKind.CHANGES_REQUESTED.value
            )
        rationale = self._build_rationale(
            coverage.open_mandatory_items,
            blocking_issue_count,
            ready_for_export,
        )

        record = ApprovalDecisionRecord(
            case_id=case_id,
            reviewer=payload.reviewer,
            note=payload.note,
            decision=decision,
            rationale=rationale,
            ready_for_export=ready_for_export,
            open_mandatory_items=coverage.open_mandatory_items,
            blocking_issue_count=blocking_issue_count,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return ApprovalDecisionSummary.model_validate(record)

    def _build_rationale(
        self,
        open_mandatory_items: int,
        blocking_issue_count: int,
        ready_for_export: bool,
    ) -> str:
        if ready_for_export:
            return (
                "All mandatory checklist items are complete and no active high-severity "
                "issues remain open."
            )

        reasons: list[str] = []
        if open_mandatory_items:
            reasons.append(
                f"{open_mandatory_items} mandatory checklist items remain unresolved"
            )
        if blocking_issue_count:
            reasons.append(
                f"{blocking_issue_count} high-severity issues still require resolution"
            )
        return "Case is not ready for export because " + " and ".join(reasons) + "."
