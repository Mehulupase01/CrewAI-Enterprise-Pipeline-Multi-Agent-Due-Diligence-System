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
    ReportTemplateKind,
    RunEventLevel,
    SectorPack,
    WorkflowRunCreate,
    WorkflowRunDetail,
    WorkflowRunEnqueueResult,
    WorkflowRunResult,
    WorkflowRunStatus,
    WorkflowRunSummary,
    WorkstreamSynthesisStatus,
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
from crewai_enterprise_pipeline_api.services.report_service import ReportService
from crewai_enterprise_pipeline_api.services.synthesis_service import SynthesisService
from crewai_enterprise_pipeline_api.services.tax_service import TaxService
from crewai_enterprise_pipeline_api.services.tech_saas_service import TechSaaSService
from crewai_enterprise_pipeline_api.services.vendor_service import VendorService
from crewai_enterprise_pipeline_api.storage.service import DocumentStorageService

logger = logging.getLogger(__name__)


class WorkflowService:
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
        self.report_service = ReportService(session)
        self.synthesis_service = SynthesisService()
        self.storage_service = DocumentStorageService()
        self.vendor_service = VendorService(session)

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
            report_template=payload.report_template.value,
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
            payload.report_template.value,
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
            report_template=payload.report_template.value,
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
        financial_summary = await self.financial_qoe_service.build_financial_summary(
            case_id,
            persist_checklist=True,
        )
        legal_summary = await self.legal_service.build_legal_summary(
            case_id,
            persist_checklist=True,
        )
        tax_summary = await self.tax_service.build_tax_summary(
            case_id,
            persist_checklist=True,
        )
        compliance_summary = await self.regulatory_service.build_compliance_matrix(
            case_id,
            persist_checklist=True,
        )
        commercial_summary = await self.commercial_service.build_commercial_summary(
            case_id,
            persist_checklist=True,
        )
        operations_summary = await self.operations_service.build_operations_summary(
            case_id,
            persist_checklist=True,
        )
        cyber_summary = await self.cyber_service.build_cyber_summary(
            case_id,
            persist_checklist=True,
        )
        forensic_summary = await self.forensic_service.build_forensic_summary(
            case_id,
            persist_checklist=True,
        )
        buy_side_analysis = None
        borrower_scorecard = None
        vendor_risk_tier = None
        tech_saas_metrics = None
        manufacturing_metrics = None
        bfsi_nbfc_metrics = None
        if case.motion_pack == "buy_side_diligence":
            buy_side_analysis = await self.buy_side_service.build_buy_side_analysis(
                case_id,
                persist_checklist=True,
            )
        elif case.motion_pack == "credit_lending":
            borrower_scorecard = await self.credit_service.build_borrower_scorecard(
                case_id,
                persist_checklist=True,
            )
        elif case.motion_pack == "vendor_onboarding":
            vendor_risk_tier = await self.vendor_service.build_vendor_risk_tier(
                case_id,
                persist_checklist=True,
            )
        if case.sector_pack == SectorPack.TECH_SAAS_SERVICES.value:
            tech_saas_metrics = await self.tech_saas_service.build_tech_saas_metrics(
                case_id,
                persist_checklist=True,
            )
        elif case.sector_pack == SectorPack.MANUFACTURING_INDUSTRIALS.value:
            manufacturing_metrics = await self.manufacturing_service.build_manufacturing_metrics(
                case_id,
                persist_checklist=True,
            )
        elif case.sector_pack == SectorPack.BFSI_NBFC.value:
            bfsi_nbfc_metrics = await self.bfsi_nbfc_service.build_bfsi_nbfc_metrics(
                case_id,
                persist_checklist=True,
            )
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        coverage = await self.checklist_service.get_coverage_summary(case_id)
        executive_memo = await self.report_service.build_executive_memo(case_id)
        executive_memo_markdown = await self.report_service.render_executive_memo_markdown(case_id)
        issue_register_markdown = await self.report_service.render_issue_register_markdown(case_id)
        if coverage is None or executive_memo is None:
            return None

        syntheses = self.synthesis_service.build_workstream_syntheses(
            case,
            run_id,
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
        synthesis_markdown = self.synthesis_service.render_markdown(case, syntheses)
        rich_report_artifacts = await self.report_service.build_rich_report_artifacts(
            case_id,
            report_template=ReportTemplateKind(run.report_template),
            workstream_syntheses=syntheses,
        )
        if rich_report_artifacts is None:
            return None

        trace_events = self._build_trace_events(
            case,
            run_id,
            coverage,
            syntheses,
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
        report_bundles = self._build_report_bundles(
            case_id,
            run_id,
            ReportTemplateKind(run.report_template),
            executive_memo_markdown,
            issue_register_markdown,
            synthesis_markdown,
            rich_report_artifacts,
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
            f"{coverage.open_mandatory_items} open mandatory checklist items. "
            f"Motion pack: {case.motion_pack}. Sector pack: {case.sector_pack}. "
            f"Report template: {run.report_template}."
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
        from crewai_enterprise_pipeline_api.agents.tools import (
            summarize_tool_usage,
            total_tool_calls,
        )

        settings = get_settings()
        seq = 1

        financial_summary = await self.financial_qoe_service.build_financial_summary(
            case_id,
            persist_checklist=True,
        )
        legal_summary = await self.legal_service.build_legal_summary(
            case_id,
            persist_checklist=True,
        )
        tax_summary = await self.tax_service.build_tax_summary(
            case_id,
            persist_checklist=True,
        )
        compliance_summary = await self.regulatory_service.build_compliance_matrix(
            case_id,
            persist_checklist=True,
        )
        commercial_summary = await self.commercial_service.build_commercial_summary(
            case_id,
            persist_checklist=True,
        )
        operations_summary = await self.operations_service.build_operations_summary(
            case_id,
            persist_checklist=True,
        )
        cyber_summary = await self.cyber_service.build_cyber_summary(
            case_id,
            persist_checklist=True,
        )
        forensic_summary = await self.forensic_service.build_forensic_summary(
            case_id,
            persist_checklist=True,
        )
        buy_side_analysis = None
        borrower_scorecard = None
        vendor_risk_tier = None
        tech_saas_metrics = None
        manufacturing_metrics = None
        bfsi_nbfc_metrics = None
        if case.motion_pack == "buy_side_diligence":
            buy_side_analysis = await self.buy_side_service.build_buy_side_analysis(
                case_id,
                persist_checklist=True,
            )
        elif case.motion_pack == "credit_lending":
            borrower_scorecard = await self.credit_service.build_borrower_scorecard(
                case_id,
                persist_checklist=True,
            )
        elif case.motion_pack == "vendor_onboarding":
            vendor_risk_tier = await self.vendor_service.build_vendor_risk_tier(
                case_id,
                persist_checklist=True,
            )
        if case.sector_pack == SectorPack.TECH_SAAS_SERVICES.value:
            tech_saas_metrics = await self.tech_saas_service.build_tech_saas_metrics(
                case_id,
                persist_checklist=True,
            )
        elif case.sector_pack == SectorPack.MANUFACTURING_INDUSTRIALS.value:
            manufacturing_metrics = await self.manufacturing_service.build_manufacturing_metrics(
                case_id,
                persist_checklist=True,
            )
        elif case.sector_pack == SectorPack.BFSI_NBFC.value:
            bfsi_nbfc_metrics = await self.bfsi_nbfc_service.build_bfsi_nbfc_metrics(
                case_id,
                persist_checklist=True,
            )
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None
        self.session.add(
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=seq,
                step_key="financial_qoe_refresh",
                title="Financial QoE summary refreshed",
                message=(
                    "Parsed "
                    f"{0 if financial_summary is None else financial_summary.statement_count} "
                    "financial statements into "
                    f"{0 if financial_summary is None else len(financial_summary.periods)} "
                    "periods."
                ),
                level=RunEventLevel.INFO.value,
            )
        )
        seq += 1
        self.session.add(
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=seq,
                step_key="legal_tax_regulatory_refresh",
                title="Legal / Tax / Regulatory summaries refreshed",
                message=(
                    "Legal artifacts: "
                    f"{0 if legal_summary is None else legal_summary.artifact_count}; "
                    "tax evidence areas: "
                    f"{self._count_known_statuses(tax_summary)}; "
                    "compliance matrix items: "
                    f"{0 if compliance_summary is None else len(compliance_summary.items)}."
                ),
                level=RunEventLevel.INFO.value,
            )
        )
        seq += 1
        self.session.add(
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=seq,
                step_key="commercial_operations_cyber_forensic_refresh",
                title="Commercial / Operations / Cyber / Forensic summaries refreshed",
                message=self._phase10_refresh_note(
                    commercial_summary,
                    operations_summary,
                    cyber_summary,
                    forensic_summary,
                    cyber_label="cyber controls",
                ),
                level=RunEventLevel.INFO.value,
            )
        )
        seq += 1
        self.session.add(
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=seq,
                step_key="motion_pack_deepening_refresh",
                title="Motion-pack deepening summary refreshed",
                message=self._phase11_refresh_note(
                    case.motion_pack,
                    buy_side_analysis,
                    borrower_scorecard,
                    vendor_risk_tier,
                ),
                level=RunEventLevel.INFO.value,
            )
        )
        seq += 1
        self.session.add(
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=seq,
                step_key="sector_pack_deepening_refresh",
                title="Sector-pack deepening summary refreshed",
                message=self._phase12_refresh_note(
                    case.sector_pack,
                    tech_saas_metrics,
                    manufacturing_metrics,
                    bfsi_nbfc_metrics,
                ),
                level=RunEventLevel.INFO.value,
            )
        )
        seq += 1
        await self.session.commit()

        # 1. Build case context
        case_ctx = build_case_context(case)
        crew, task_map, tool_map = build_due_diligence_crew(
            case_ctx,
            settings,
            financial_summary=financial_summary,
            legal_summary=legal_summary,
            tax_summary=tax_summary,
            compliance_summary=compliance_summary,
            commercial_summary=commercial_summary,
            operations_summary=operations_summary,
            cyber_summary=cyber_summary,
            forensic_summary=forensic_summary,
            buy_side_analysis=buy_side_analysis,
            borrower_scorecard=borrower_scorecard,
            vendor_risk_tier=vendor_risk_tier,
            tech_saas_metrics=tech_saas_metrics,
            manufacturing_metrics=manufacturing_metrics,
            bfsi_nbfc_metrics=bfsi_nbfc_metrics,
        )
        total_tools = sum(len(tools) for tools in tool_map.values())
        self.session.add(
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=seq,
                step_key="crew_initialized",
                title="CrewAI crew initialized",
                message=(
            f"Built crew with {len(case_ctx.workstreams)} workstream agents "
            f"and 1 coordinator. LLM: {settings.llm_provider}/{settings.llm_model}. "
            f"Scoped tools attached: {total_tools}."
                ),
                level=RunEventLevel.INFO.value,
            )
        )
        seq += 1
        await self.session.commit()

        # 2. Build and run the crew
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
            tool_summary = summarize_tool_usage(tool_map.get(ws_domain, []))

            self.session.add(
                RunTraceEventRecord(
                    run_id=run_id,
                    sequence_number=seq,
                    step_key=f"agent_{ws_domain}",
                    title=f"{ws_domain.replace('_', ' ').title()} analysis complete",
                    message=f"{synthesis.headline} Tools: {tool_summary}",
                    level=RunEventLevel.INFO.value,
                )
            )
            seq += 1

        motion_pack_task_output = None
        if hasattr(crew_output, "tasks_output"):
            for task_output in crew_output.tasks_output:
                if getattr(task_output, "name", None) == "motion_pack_analysis":
                    motion_pack_task_output = task_output
                    break
        if motion_pack_task_output is not None:
            raw_preview = str(getattr(motion_pack_task_output, "raw", ""))[:240]
            motion_tool_summary = summarize_tool_usage(tool_map.get("motion_pack_specialist", []))
            self.session.add(
                RunTraceEventRecord(
                    run_id=run_id,
                    sequence_number=seq,
                    step_key="motion_pack_analysis",
                    title="Motion-pack specialist analysis complete",
                    message=f"{raw_preview} Tools: {motion_tool_summary}",
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

        coordinator_tool_summary = summarize_tool_usage(tool_map.get("coordinator", []))
        self.session.add(
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=seq,
                step_key="coordinator_synthesis",
                title="Lead coordinator synthesis complete",
                message=f"{exec_summary[:240]} Tools: {coordinator_tool_summary}",
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
        issue_register_markdown = await self.report_service.render_issue_register_markdown(case_id)
        synthesis_lines = [f"# Workstream Syntheses: {case.name}\n"]
        for s in syntheses:
            synthesis_lines.extend(
                [
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
                ]
            )
        synthesis_markdown = "\n".join(synthesis_lines)
        rich_report_artifacts = await self.report_service.build_rich_report_artifacts(
            case_id,
            report_template=ReportTemplateKind(run.report_template),
            workstream_syntheses=syntheses,
        )
        if rich_report_artifacts is None:
            return None

        report_bundles = self._build_report_bundles(
            case_id,
            run_id,
            ReportTemplateKind(run.report_template),
            executive_memo_markdown,
            issue_register_markdown,
            synthesis_markdown,
            rich_report_artifacts,
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
                    f"{len(syntheses)} workstream syntheses via CrewAI agents. "
                    f"Tool calls recorded: {total_tool_calls(tool_map)}."
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
            f"LLM: {settings.llm_provider}/{settings.llm_model}. "
            f"Tool calls: {total_tool_calls(tool_map)}. Motion pack: {case.motion_pack}. "
            f"Sector pack: {case.sector_pack}. Report template: {run.report_template}."
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
                if hasattr(to, "pydantic") and isinstance(to.pydantic, ExecutiveSummaryOutput):
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
    ) -> list[RunTraceEventRecord]:
        latest_approval = case.approvals[-1] if case.approvals else None
        approval_note = (
            "No approval review recorded yet."
            if latest_approval is None
            else f"Latest decision: {latest_approval.decision}"
        )
        financial_note = (
            "No structured financial statements detected yet."
            if financial_summary is None or not financial_summary.periods
            else (
                f"Parsed {financial_summary.statement_count} statements into "
                f"{len(financial_summary.periods)} financial periods."
            )
        )
        phase9_note = (
            "No structured legal/tax/regulatory summaries detected yet."
            if (legal_summary is None and tax_summary is None and compliance_summary is None)
            else (
                "Legal artifacts: "
                f"{0 if legal_summary is None else legal_summary.artifact_count}; "
                "tax areas with evidence: "
                f"{self._count_known_statuses(tax_summary)}; "
                "compliance matrix items: "
                f"{0 if compliance_summary is None else len(compliance_summary.items)}."
            )
        )
        phase10_note = (
            "No structured commercial/operations/cyber/forensic summaries detected yet."
            if (
                commercial_summary is None
                and operations_summary is None
                and cyber_summary is None
                and forensic_summary is None
            )
            else self._phase10_refresh_note(
                commercial_summary,
                operations_summary,
                cyber_summary,
                forensic_summary,
                cyber_label="cyber controls with evidence",
            )
        )
        phase11_note = self._phase11_refresh_note(
            case.motion_pack,
            buy_side_analysis,
            borrower_scorecard,
            vendor_risk_tier,
        )
        phase12_note = self._phase12_refresh_note(
            case.sector_pack,
            tech_saas_metrics,
            manufacturing_metrics,
            bfsi_nbfc_metrics,
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
                step_key="financial_qoe_refresh",
                title="Financial QoE summary refreshed",
                message=financial_note,
                level=RunEventLevel.INFO.value,
            ),
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=3,
                step_key="legal_tax_regulatory_refresh",
                title="Legal / Tax / Regulatory summaries refreshed",
                message=phase9_note,
                level=RunEventLevel.INFO.value,
            ),
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=4,
                step_key="commercial_operations_cyber_forensic_refresh",
                title="Commercial / Operations / Cyber / Forensic summaries refreshed",
                message=phase10_note,
                level=RunEventLevel.INFO.value,
            ),
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=5,
                step_key="motion_pack_deepening_refresh",
                title="Motion-pack deepening summary refreshed",
                message=phase11_note,
                level=RunEventLevel.INFO.value,
            ),
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=6,
                step_key="sector_pack_deepening_refresh",
                title="Sector-pack deepening summary refreshed",
                message=phase12_note,
                level=RunEventLevel.INFO.value,
            ),
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=7,
                step_key="issue_triage",
                title="Issue register reviewed",
                message=(
                    f"Detected {len(case.issues)} total issues across the current case state."
                ),
                level=RunEventLevel.INFO.value,
            ),
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=8,
                step_key="coverage_check",
                title="Checklist coverage computed",
                message=(f"{coverage.open_mandatory_items} mandatory checklist items remain open."),
                level=(
                    RunEventLevel.WARNING.value
                    if coverage.open_mandatory_items
                    else RunEventLevel.INFO.value
                ),
            ),
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=9,
                step_key="approval_snapshot",
                title="Approval state captured",
                message=approval_note,
                level=RunEventLevel.INFO.value,
            ),
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=10,
                step_key="workstream_synthesis",
                title="Workstream syntheses generated",
                message=(f"Generated {len(syntheses)} workstream summaries for the current run."),
                level=RunEventLevel.INFO.value,
            ),
            RunTraceEventRecord(
                run_id=run_id,
                sequence_number=11,
                step_key="report_bundle_generation",
                title="Report bundles generated",
                message=(
                    "Executive memo, issue register, workstream synthesis, "
                    "full report, financial annex, DOCX, and PDF bundles were rendered."
                ),
                level=RunEventLevel.INFO.value,
            ),
        ]

    def _build_report_bundles(
        self,
        case_id: str,
        run_id: str,
        report_template: ReportTemplateKind,
        executive_memo_markdown: str | None,
        issue_register_markdown: str | None,
        synthesis_markdown: str | None,
        rich_report_artifacts,
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
                    file_name="executive_memo.md",
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
                    file_name="issue_register.md",
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
                    file_name="workstream_syntheses.md",
                )
            )
        if rich_report_artifacts is not None:
            bundles.append(
                ReportBundleRecord(
                    case_id=case_id,
                    run_id=run_id,
                    bundle_kind=ReportBundleKind.FULL_REPORT_MARKDOWN.value,
                    title=rich_report_artifacts.full_report_title,
                    format="markdown",
                    summary=(
                        f"{report_template.value.replace('_', ' ').title()} template full report "
                        "rendered with Jinja2."
                    ),
                    content=rich_report_artifacts.full_report_markdown,
                    file_name=f"full_report_{report_template.value}.md",
                )
            )
            bundles.append(
                ReportBundleRecord(
                    case_id=case_id,
                    run_id=run_id,
                    bundle_kind=ReportBundleKind.FINANCIAL_ANNEX_MARKDOWN.value,
                    title="Financial Annex",
                    format="markdown",
                    summary="Detailed financial annex rendered for export-ready reporting.",
                    content=rich_report_artifacts.financial_annex_markdown,
                    file_name="financial_annex.md",
                )
            )

            docx_file_name = f"full_report_{report_template.value}.docx"
            docx_artifact = self.storage_service.store_bytes(
                case_id=case_id,
                artifact_id=f"{run_id}-{ReportBundleKind.FULL_REPORT_DOCX.value}",
                filename=docx_file_name,
                content=rich_report_artifacts.docx_bytes,
            )
            bundles.append(
                ReportBundleRecord(
                    case_id=case_id,
                    run_id=run_id,
                    bundle_kind=ReportBundleKind.FULL_REPORT_DOCX.value,
                    title=f"{rich_report_artifacts.full_report_title} DOCX",
                    format="docx",
                    summary="Branded DOCX report with cover page, table of contents, and tables.",
                    content="Binary DOCX artifact generated for this workflow run.",
                    file_name=docx_file_name,
                    storage_path=docx_artifact.storage_path,
                    sha256_digest=docx_artifact.sha256_digest,
                    byte_size=docx_artifact.byte_size,
                )
            )

            pdf_file_name = f"full_report_{report_template.value}.pdf"
            pdf_artifact = self.storage_service.store_bytes(
                case_id=case_id,
                artifact_id=f"{run_id}-{ReportBundleKind.FULL_REPORT_PDF.value}",
                filename=pdf_file_name,
                content=rich_report_artifacts.pdf_bytes,
            )
            bundles.append(
                ReportBundleRecord(
                    case_id=case_id,
                    run_id=run_id,
                    bundle_kind=ReportBundleKind.FULL_REPORT_PDF.value,
                    title=f"{rich_report_artifacts.full_report_title} PDF",
                    format="pdf",
                    summary=(
                        "Readable PDF rendition of the full report for board and lender "
                        "sharing."
                    ),
                    content="Binary PDF artifact generated for this workflow run.",
                    file_name=pdf_file_name,
                    storage_path=pdf_artifact.storage_path,
                    sha256_digest=pdf_artifact.sha256_digest,
                    byte_size=pdf_artifact.byte_size,
                )
            )
        return bundles

    @staticmethod
    def _count_known_statuses(summary) -> int:
        if summary is None:
            return 0
        return len([item for item in summary.items if item.status.value != "unknown"])

    @staticmethod
    def _count_known_cyber_controls(summary) -> int:
        if summary is None:
            return 0
        return len([item for item in summary.controls if item.status.value != "unknown"])

    def _phase10_refresh_note(
        self,
        commercial_summary,
        operations_summary,
        cyber_summary,
        forensic_summary,
        *,
        cyber_label: str,
    ) -> str:
        commercial_count = (
            0 if commercial_summary is None else len(commercial_summary.concentration_signals)
        )
        operations_count = (
            0 if operations_summary is None else len(operations_summary.dependency_signals)
        )
        cyber_count = self._count_known_cyber_controls(cyber_summary)
        forensic_count = 0 if forensic_summary is None else len(forensic_summary.flags)
        return (
            f"Commercial signals: {commercial_count}; "
            f"operations dependencies: {operations_count}; "
            f"{cyber_label}: {cyber_count}; "
            f"forensic flags: {forensic_count}."
        )

    def _phase11_refresh_note(
        self,
        motion_pack: str,
        buy_side_analysis,
        borrower_scorecard,
        vendor_risk_tier,
    ) -> str:
        if motion_pack == "buy_side_diligence" and buy_side_analysis is not None:
            return (
                f"Valuation bridge items: {len(buy_side_analysis.valuation_bridge)}; "
                f"SPA issues: {len(buy_side_analysis.spa_issues)}; "
                f"PMI risks: {len(buy_side_analysis.pmi_risks)}."
            )
        if motion_pack == "credit_lending" and borrower_scorecard is not None:
            return (
                f"Borrower score: {borrower_scorecard.overall_score}/100; "
                f"collateral score: {borrower_scorecard.collateral.score}/100; "
                f"covenant items: {len(borrower_scorecard.covenant_tracking)}."
            )
        if motion_pack == "vendor_onboarding" and vendor_risk_tier is not None:
            return (
                f"Vendor tier: {vendor_risk_tier.tier}; "
                f"overall score: {vendor_risk_tier.overall_score}/100; "
                f"questionnaire sections: {len(vendor_risk_tier.questionnaire)}."
            )
        return "No structured motion-pack summary detected yet."

    def _phase12_refresh_note(
        self,
        sector_pack: str,
        tech_saas_metrics,
        manufacturing_metrics,
        bfsi_nbfc_metrics,
    ) -> str:
        if sector_pack == SectorPack.TECH_SAAS_SERVICES.value and tech_saas_metrics is not None:
            fragments: list[str] = []
            if tech_saas_metrics.arr is not None:
                fragments.append(f"ARR {tech_saas_metrics.arr:.2f}")
            if tech_saas_metrics.nrr is not None:
                fragments.append(f"NRR {tech_saas_metrics.nrr:.0%}")
            if tech_saas_metrics.payback_months is not None:
                fragments.append(f"payback {tech_saas_metrics.payback_months:.1f} months")
            return (
                "Tech/SaaS metrics refreshed: "
                + (", ".join(fragments) if fragments else "structured sector metrics available")
                + "."
            )
        if (
            sector_pack == SectorPack.MANUFACTURING_INDUSTRIALS.value
            and manufacturing_metrics is not None
        ):
            fragments = []
            if manufacturing_metrics.capacity_utilization is not None:
                fragments.append(
                    f"capacity {manufacturing_metrics.capacity_utilization:.0%}"
                )
            if manufacturing_metrics.dio is not None:
                fragments.append(f"DIO {manufacturing_metrics.dio:.0f} days")
            if manufacturing_metrics.asset_turnover is not None:
                fragments.append(
                    f"asset turnover {manufacturing_metrics.asset_turnover:.2f}x"
                )
            return (
                "Manufacturing metrics refreshed: "
                + (", ".join(fragments) if fragments else "structured plant metrics available")
                + "."
            )
        if sector_pack == SectorPack.BFSI_NBFC.value and bfsi_nbfc_metrics is not None:
            fragments = []
            if bfsi_nbfc_metrics.gnpa is not None:
                fragments.append(f"GNPA {bfsi_nbfc_metrics.gnpa:.2%}")
            if bfsi_nbfc_metrics.crar is not None:
                fragments.append(f"CRAR {bfsi_nbfc_metrics.crar:.2%}")
            if bfsi_nbfc_metrics.alm_mismatch is not None:
                fragments.append(f"ALM mismatch {bfsi_nbfc_metrics.alm_mismatch:.2%}")
            return (
                "BFSI/NBFC metrics refreshed: "
                + (
                    ", ".join(fragments)
                    if fragments
                    else "structured balance-sheet metrics available"
                )
                + "."
            )
        return "No structured sector-pack summary detected yet."
