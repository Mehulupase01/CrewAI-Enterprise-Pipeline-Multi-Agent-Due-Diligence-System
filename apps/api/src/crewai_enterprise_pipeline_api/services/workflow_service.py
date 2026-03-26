from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crewai_enterprise_pipeline_api.db.models import (
    ReportBundleRecord,
    RunTraceEventRecord,
    WorkflowRunRecord,
    WorkstreamSynthesisRecord,
)
from crewai_enterprise_pipeline_api.domain.models import (
    ReportBundleKind,
    RunEventLevel,
    WorkflowRunCreate,
    WorkflowRunDetail,
    WorkflowRunResult,
    WorkflowRunStatus,
    WorkflowRunSummary,
)
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.services.checklist_service import ChecklistService
from crewai_enterprise_pipeline_api.services.report_service import ReportService
from crewai_enterprise_pipeline_api.services.synthesis_service import SynthesisService


class WorkflowService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)
        self.checklist_service = ChecklistService(session)
        self.report_service = ReportService(session)
        self.synthesis_service = SynthesisService()

    async def list_runs(self, case_id: str) -> list[WorkflowRunSummary]:
        result = await self.session.execute(
            select(WorkflowRunRecord)
            .where(WorkflowRunRecord.case_id == case_id)
            .order_by(WorkflowRunRecord.created_at.desc())
        )
        return [WorkflowRunSummary.model_validate(item) for item in result.scalars().all()]

    async def get_run(self, case_id: str, run_id: str) -> WorkflowRunDetail | None:
        result = await self.session.execute(
            select(WorkflowRunRecord)
            .where(WorkflowRunRecord.case_id == case_id, WorkflowRunRecord.id == run_id)
            .options(
                selectinload(WorkflowRunRecord.trace_events),
                selectinload(WorkflowRunRecord.report_bundles),
                selectinload(WorkflowRunRecord.workstream_syntheses),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return WorkflowRunDetail.model_validate(record)

    async def execute_run(
        self,
        case_id: str,
        payload: WorkflowRunCreate,
    ) -> WorkflowRunResult | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        run = WorkflowRunRecord(
            case_id=case_id,
            requested_by=payload.requested_by,
            note=payload.note,
            status=WorkflowRunStatus.RUNNING.value,
            started_at=datetime.now(UTC),
        )
        self.session.add(run)
        await self.session.flush()
        run_id = run.id

        coverage = await self.checklist_service.get_coverage_summary(case_id)
        executive_memo = await self.report_service.build_executive_memo(case_id)
        executive_memo_markdown = await self.report_service.render_executive_memo_markdown(
            case_id
        )
        issue_register_markdown = await self.report_service.render_issue_register_markdown(
            case_id
        )
        if coverage is None or executive_memo is None:
            return None

        syntheses = self.synthesis_service.build_workstream_syntheses(case, run_id)
        synthesis_markdown = self.synthesis_service.render_markdown(case, syntheses)

        trace_events = self._build_trace_events(case, run_id, coverage, syntheses)
        report_bundles = self._build_report_bundles(
            case_id,
            run_id,
            executive_memo_markdown,
            issue_register_markdown,
            synthesis_markdown,
        )

        self.session.add_all(trace_events)
        self.session.add_all(report_bundles)
        self.session.add_all(syntheses)

        run.status = WorkflowRunStatus.COMPLETED.value
        run.completed_at = datetime.now(UTC)
        run.summary = (
            f"Generated {len(report_bundles)} report bundles, "
            f"{len(syntheses)} workstream syntheses, with "
            f"{len(case.issues)} issues and "
            f"{coverage.open_mandatory_items} open mandatory checklist items."
        )
        await self.session.commit()
        self.session.expire_all()

        run_detail = await self.get_run(case_id, run_id)
        if run_detail is None:
            return None

        return WorkflowRunResult(run=run_detail, executive_memo=executive_memo)

    def _build_trace_events(
        self,
        case,
        run_id: str,
        coverage,
        syntheses: list[WorkstreamSynthesisRecord],
    ) -> list[RunTraceEventRecord]:
        latest_approval = case.approvals[-1] if case.approvals else None
        approval_note = (
            "No approval review recorded yet."
            if latest_approval is None
            else f"Latest decision: {latest_approval.decision}"
        )
        return [
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=1,
                step_key="case_snapshot",
                title="Case snapshot loaded",
                message=(
                    f"Loaded {len(case.documents)} documents, {len(case.evidence_items)} "
                    f"evidence nodes, and {len(case.request_items)} request items."
                ),
                level=RunEventLevel.INFO.value,
            ),
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=2,
                step_key="issue_triage",
                title="Issue register reviewed",
                message=(
                    f"Detected {len(case.issues)} total issues across the current case state."
                ),
                level=RunEventLevel.INFO.value,
            ),
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=3,
                step_key="coverage_check",
                title="Checklist coverage computed",
                message=(
                    f"{coverage.open_mandatory_items} mandatory checklist items remain open."
                ),
                level=(
                    RunEventLevel.WARNING.value
                    if coverage.open_mandatory_items
                    else RunEventLevel.INFO.value
                ),
            ),
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=4,
                step_key="approval_snapshot",
                title="Approval state captured",
                message=approval_note,
                level=RunEventLevel.INFO.value,
            ),
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=5,
                step_key="workstream_synthesis",
                title="Workstream syntheses generated",
                message=(
                    f"Generated {len(syntheses)} workstream summaries for the current run."
                ),
                level=RunEventLevel.INFO.value,
            ),
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=6,
                step_key="report_bundle_generation",
                title="Report bundles generated",
                message=(
                    "Executive memo, issue register, and workstream synthesis bundles "
                    "were rendered."
                ),
                level=RunEventLevel.INFO.value,
            ),
        ]

    def _build_report_bundles(
        self,
        case_id: str,
        run_id: str,
        executive_memo_markdown: str | None,
        issue_register_markdown: str | None,
        synthesis_markdown: str | None,
    ) -> list[ReportBundleRecord]:
        bundles: list[ReportBundleRecord] = []
        if executive_memo_markdown is not None:
            bundles.append(
                ReportBundleRecord(
                    case_id=case_id,
                    run_id=run_id,
                    bundle_kind=ReportBundleKind.EXECUTIVE_MEMO_MARKDOWN.value,
                    title="Executive Memo",
                    format="markdown",
                    summary="Investor-style memo generated from the current case state.",
                    content=executive_memo_markdown,
                )
            )
        if issue_register_markdown is not None:
            bundles.append(
                ReportBundleRecord(
                    case_id=case_id,
                    run_id=run_id,
                    bundle_kind=ReportBundleKind.ISSUE_REGISTER_MARKDOWN.value,
                    title="Issue Register",
                    format="markdown",
                    summary="Sorted issue register snapshot generated from the current case.",
                    content=issue_register_markdown,
                )
            )
        if synthesis_markdown is not None:
            bundles.append(
                ReportBundleRecord(
                    case_id=case_id,
                    run_id=run_id,
                    bundle_kind=ReportBundleKind.WORKSTREAM_SYNTHESIS_MARKDOWN.value,
                    title="Workstream Syntheses",
                    format="markdown",
                    summary="Run-level synthesis by diligence workstream.",
                    content=synthesis_markdown,
                )
            )
        return bundles
