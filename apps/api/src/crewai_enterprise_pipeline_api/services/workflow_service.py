from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crewai_enterprise_pipeline_api.core.settings import get_settings
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
    WorkflowRunEnqueueResult,
    WorkflowRunResult,
    WorkflowRunStatus,
    WorkflowRunSummary,
    WorkstreamSynthesisStatus,
)
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.services.checklist_service import ChecklistService
from crewai_enterprise_pipeline_api.services.report_service import ReportService
from crewai_enterprise_pipeline_api.services.synthesis_service import SynthesisService

logger = logging.getLogger(__name__)


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
                selectinload(WorkflowRunRecord.export_packages),
                selectinload(WorkflowRunRecord.workstream_syntheses),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return WorkflowRunDetail.model_validate(record)

    async def enqueue_run(
        self,
        case_id: str,
        payload: WorkflowRunCreate,
        redis_pool,
    ) -> WorkflowRunEnqueueResult | None:
        """Create a QUEUED run record and enqueue it via arq for background execution."""
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        run = WorkflowRunRecord(
            case_id=case_id,
            requested_by=payload.requested_by,
            note=payload.note,
            status=WorkflowRunStatus.QUEUED.value,
        )
        self.session.add(run)
        await self.session.commit()

        from crewai_enterprise_pipeline_api.worker import run_workflow_job

        await redis_pool.enqueue_job(
            run_workflow_job.__name__,
            case_id,
            payload.requested_by,
            payload.note,
        )
        logger.info("Enqueued workflow run %s for case %s", run.id, case_id)

        return WorkflowRunEnqueueResult(run_id=run.id, case_id=case_id)

    def _crew_available(self) -> bool:
        """Check if CrewAI agents should be activated (AD-001 deterministic fallback)."""
        settings = get_settings()
        return settings.llm_provider != "none" and bool(settings.llm_api_key)

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

        try:
            if self._crew_available():
                return await self._execute_crew_run(case, run, run_id, case_id)
            return await self._execute_deterministic_run(case, run, run_id, case_id)
        except Exception as exc:
            logger.exception("Workflow run %s failed", run_id)
            run.status = WorkflowRunStatus.FAILED.value
            run.completed_at = datetime.now(UTC)
            run.summary = f"Run failed: {exc}"
            self.session.add(
                RunTraceEventRecord(
                    run_id=run_id,
                    sequence_number=0,
                    step_key="run_failure",
                    title="Workflow run failed",
                    message=str(exc),
                    level=RunEventLevel.WARNING.value,
                )
            )
            await self.session.commit()
            raise

    async def _execute_deterministic_run(
        self,
        case,
        run: WorkflowRunRecord,
        run_id: str,
        case_id: str,
    ) -> WorkflowRunResult | None:
        """Original deterministic workflow — no LLM, pure template logic."""
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

    async def _execute_crew_run(
        self,
        case,
        run: WorkflowRunRecord,
        run_id: str,
        case_id: str,
    ) -> WorkflowRunResult | None:
        """CrewAI-powered workflow — LLM agents analyze each workstream."""
        from crewai_enterprise_pipeline_api.agents.crew import (
            build_case_context,
            build_due_diligence_crew,
            run_crew,
        )

        settings = get_settings()
        seq = 1

        # 1. Build case context
        case_ctx = build_case_context(case)
        self.session.add(
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=seq,
                step_key="crew_initialized",
                title="CrewAI crew initialized",
                message=(
                    f"Built crew with {len(case_ctx.workstreams)} workstream agents "
                    f"and 1 coordinator. LLM: {settings.llm_provider}/{settings.llm_model}."
                ),
                level=RunEventLevel.INFO.value,
            )
        )
        seq += 1
        await self.session.commit()

        # 2. Build and run the crew
        crew, task_map = build_due_diligence_crew(case_ctx, settings)
        logger.info(
            "Starting CrewAI kickoff for case %s with %d workstream agents",
            case_id,
            len(case_ctx.workstreams),
        )
        crew_output = await run_crew(crew)

        # 3. Parse workstream task outputs → syntheses + trace events
        syntheses: list[WorkstreamSynthesisRecord] = []
        for ws_domain, task_name in task_map.items():
            task_output = self._find_task_output(crew_output, task_name, ws_domain)

            if task_output is not None:
                status = self._normalize_ws_status(task_output.status)
                synthesis = WorkstreamSynthesisRecord(
                    case_id=case_id,
                    run_id=run_id,
                    workstream_domain=ws_domain,
                    status=status,
                    headline=task_output.headline,
                    narrative=task_output.narrative,
                    finding_count=task_output.finding_count,
                    blocker_count=task_output.blocker_count,
                    confidence=max(0.0, min(1.0, task_output.confidence)),
                    recommended_next_action=task_output.recommended_next_action,
                )
            else:
                synthesis = WorkstreamSynthesisRecord(
                    case_id=case_id,
                    run_id=run_id,
                    workstream_domain=ws_domain,
                    status=WorkstreamSynthesisStatus.NEEDS_FOLLOW_UP.value,
                    headline=f"{ws_domain.replace('_', ' ').title()} analysis "
                    f"returned unstructured output.",
                    narrative=self._get_raw_task_output(crew_output, ws_domain),
                    finding_count=0,
                    blocker_count=0,
                    confidence=0.3,
                    recommended_next_action="Review raw agent output manually.",
                )
            syntheses.append(synthesis)

            self.session.add(
                RunTraceEventRecord(
                    run_id=run_id,
                    sequence_number=seq,
                    step_key=f"agent_{ws_domain}",
                    title=f"{ws_domain.replace('_', ' ').title()} analysis complete",
                    message=synthesis.headline,
                    level=RunEventLevel.INFO.value,
                )
            )
            seq += 1

        # 4. Parse coordinator output → executive memo
        exec_output = self._find_executive_output(crew_output)
        if exec_output is not None:
            exec_summary = exec_output.executive_summary
            risk_assessment = exec_output.overall_risk_assessment
            top_risks_text = "\n".join(f"- {r}" for r in exec_output.top_risks)
            next_steps_text = "\n".join(f"- {s}" for s in exec_output.recommended_next_steps)
            coordinator_narrative = (
                f"{exec_summary}\n\n"
                f"**Overall Risk: {risk_assessment}**\n\n"
                f"## Top Risks\n{top_risks_text}\n\n"
                f"## Next Steps\n{next_steps_text}"
            )
        else:
            raw = str(crew_output.raw) if hasattr(crew_output, "raw") else str(crew_output)
            coordinator_narrative = raw[:4000]
            exec_summary = coordinator_narrative[:500]

        self.session.add(
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=seq,
                step_key="coordinator_synthesis",
                title="Lead coordinator synthesis complete",
                message=exec_summary[:300],
                level=RunEventLevel.INFO.value,
            )
        )
        seq += 1

        # 5. Build report bundles
        executive_memo_markdown = (
            f"# Executive Memo: {case.name}\n\n"
            f"Target: {case.target_name}\n"
            f"Motion Pack: {case.motion_pack}\n\n"
            f"{coordinator_narrative}"
        )
        issue_register_markdown = await self.report_service.render_issue_register_markdown(
            case_id
        )
        synthesis_lines = [f"# Workstream Syntheses: {case.name}\n"]
        for s in syntheses:
            synthesis_lines.extend([
                f"\n## {s.workstream_domain.replace('_', ' ').title()}",
                f"Status: {s.status}",
                f"Headline: {s.headline}",
                "",
                s.narrative,
                "",
                f"Findings: {s.finding_count}",
                f"Blockers: {s.blocker_count}",
                f"Confidence: {s.confidence:.2f}",
                f"Next action: {s.recommended_next_action}",
                "",
            ])
        synthesis_markdown = "\n".join(synthesis_lines)

        report_bundles = self._build_report_bundles(
            case_id,
            run_id,
            executive_memo_markdown,
            issue_register_markdown,
            synthesis_markdown,
        )

        self.session.add_all(report_bundles)
        self.session.add_all(syntheses)

        self.session.add(
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=seq,
                step_key="report_bundle_generation",
                title="Report bundles generated",
                message=(
                    f"Generated {len(report_bundles)} report bundles and "
                    f"{len(syntheses)} workstream syntheses via CrewAI agents."
                ),
                level=RunEventLevel.INFO.value,
            )
        )

        # 6. Finalize
        run.status = WorkflowRunStatus.COMPLETED.value
        run.completed_at = datetime.now(UTC)
        run.summary = (
            f"CrewAI run: {len(syntheses)} workstream analyses, "
            f"{len(report_bundles)} report bundles. "
            f"LLM: {settings.llm_provider}/{settings.llm_model}."
        )

        # Build executive memo via deterministic service for the response object
        executive_memo = await self.report_service.build_executive_memo(case_id)

        await self.session.commit()
        self.session.expire_all()

        run_detail = await self.get_run(case_id, run_id)
        if run_detail is None:
            return None
        return WorkflowRunResult(run=run_detail, executive_memo=executive_memo)

    def _find_task_output(self, crew_output, task_name: str, ws_domain: str):
        """Extract pydantic output for a workstream task from CrewAI result."""
        from crewai_enterprise_pipeline_api.agents.models import WorkstreamAnalysisOutput

        if hasattr(crew_output, "tasks_output"):
            for to in crew_output.tasks_output:
                name = getattr(to, "name", None) or ""
                if name == task_name or ws_domain in name:
                    if hasattr(to, "pydantic") and isinstance(
                        to.pydantic, WorkstreamAnalysisOutput
                    ):
                        return to.pydantic
        return None

    def _find_executive_output(self, crew_output):
        """Extract the coordinator's pydantic output from CrewAI result."""
        from crewai_enterprise_pipeline_api.agents.models import ExecutiveSummaryOutput

        if hasattr(crew_output, "pydantic") and isinstance(
            crew_output.pydantic, ExecutiveSummaryOutput
        ):
            return crew_output.pydantic

        if hasattr(crew_output, "tasks_output"):
            for to in crew_output.tasks_output:
                if hasattr(to, "pydantic") and isinstance(
                    to.pydantic, ExecutiveSummaryOutput
                ):
                    return to.pydantic
        return None

    def _get_raw_task_output(self, crew_output, ws_domain: str) -> str:
        """Get raw text output for a workstream as fallback."""
        if hasattr(crew_output, "tasks_output"):
            for to in crew_output.tasks_output:
                name = getattr(to, "name", None) or ""
                if ws_domain in name:
                    raw = getattr(to, "raw", None)
                    if raw:
                        return str(raw)[:4000]
        return f"No output captured for {ws_domain}."

    @staticmethod
    def _normalize_ws_status(status_str: str) -> str:
        """Normalize agent-returned status string to a valid WorkstreamSynthesisStatus."""
        normalized = status_str.strip().lower().replace(" ", "_").replace("-", "_")
        valid = {s.value for s in WorkstreamSynthesisStatus}
        if normalized in valid:
            return normalized
        if "block" in normalized:
            return WorkstreamSynthesisStatus.BLOCKED.value
        if "follow" in normalized or "need" in normalized:
            return WorkstreamSynthesisStatus.NEEDS_FOLLOW_UP.value
        return WorkstreamSynthesisStatus.READY_FOR_REVIEW.value

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
