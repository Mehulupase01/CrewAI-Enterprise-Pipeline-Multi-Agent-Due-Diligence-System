"""CrewAI crew factory for due diligence workflow runs."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from crewai import LLM, Agent, Crew, Process, Task

from crewai_enterprise_pipeline_api.agents.compliance_tools import format_phase9_snapshot
from crewai_enterprise_pipeline_api.agents.config import (
    COORDINATOR_CONFIG,
    WORKSTREAM_AGENT_CONFIGS,
    motion_pack_context,
    sector_pack_context,
)
from crewai_enterprise_pipeline_api.agents.financial_tools import format_financial_snapshot
from crewai_enterprise_pipeline_api.agents.models import (
    ExecutiveSummaryOutput,
    MotionPackAnalysisOutput,
    WorkstreamAnalysisOutput,
)
from crewai_enterprise_pipeline_api.agents.packs.buy_side_crew import (
    BUY_SIDE_SPECIALIST_CONFIG,
    build_buy_side_prompt,
)
from crewai_enterprise_pipeline_api.agents.packs.credit_crew import (
    CREDIT_SPECIALIST_CONFIG,
    build_credit_prompt,
)
from crewai_enterprise_pipeline_api.agents.packs.vendor_crew import (
    VENDOR_SPECIALIST_CONFIG,
    build_vendor_prompt,
)
from crewai_enterprise_pipeline_api.agents.phase10_tools import format_phase10_snapshot
from crewai_enterprise_pipeline_api.agents.phase11_tools import format_phase11_snapshot
from crewai_enterprise_pipeline_api.agents.phase12_tools import format_phase12_snapshot
from crewai_enterprise_pipeline_api.agents.tools import (
    build_case_tools,
    build_workstream_tools,
)
from crewai_enterprise_pipeline_api.core.telemetry import observe_llm_run
from crewai_enterprise_pipeline_api.domain.models import WorkstreamDomain


@dataclass
class ChunkContext:
    """Pre-loaded chunk metadata for case-aware evidence tools."""

    chunk_id: str
    artifact_id: str
    document_title: str
    document_kind: str
    source_kind: str
    section_title: str | None
    page_number: int | None
    text: str


@dataclass
class WorkstreamContext:
    """Pre-loaded data for a single workstream."""

    domain: str
    evidence_items: list[Any] = field(default_factory=list)
    issues: list[Any] = field(default_factory=list)
    checklist_items: list[Any] = field(default_factory=list)
    chunks: list[ChunkContext] = field(default_factory=list)


@dataclass
class CaseContext:
    """All data needed by the crew, queried once before kickoff."""

    case_id: str
    case_name: str
    target_name: str
    country: str
    motion_pack: str
    sector_pack: str
    document_count: int
    chunk_count: int = 0
    chunks: list[ChunkContext] = field(default_factory=list)
    workstreams: dict[str, WorkstreamContext] = field(default_factory=dict)


def build_case_context(case) -> CaseContext:
    """Build CaseContext from a loaded CaseRecord with eager-loaded relations."""
    ctx = CaseContext(
        case_id=case.id,
        case_name=case.name,
        target_name=case.target_name,
        country=case.country,
        motion_pack=case.motion_pack,
        sector_pack=case.sector_pack,
        document_count=len(case.documents),
    )

    chunks_by_artifact: dict[str, list[ChunkContext]] = {}
    for document in case.documents:
        document_chunks: list[ChunkContext] = []
        for chunk in getattr(document, "chunks", []):
            chunk_ctx = ChunkContext(
                chunk_id=chunk.id,
                artifact_id=document.id,
                document_title=document.title,
                document_kind=document.document_kind,
                source_kind=document.source_kind,
                section_title=chunk.section_title,
                page_number=chunk.page_number,
                text=chunk.text,
            )
            document_chunks.append(chunk_ctx)
            ctx.chunks.append(chunk_ctx)
        chunks_by_artifact[document.id] = document_chunks
    ctx.chunk_count = len(ctx.chunks)

    for ws in WorkstreamDomain:
        ws_ctx = WorkstreamContext(domain=ws.value)
        ws_ctx.evidence_items = [
            item for item in case.evidence_items if item.workstream_domain == ws.value
        ]
        ws_ctx.issues = [item for item in case.issues if item.workstream_domain == ws.value]
        ws_ctx.checklist_items = [
            item for item in case.checklist_items if item.workstream_domain == ws.value
        ]
        artifact_ids = {
            item.artifact_id for item in ws_ctx.evidence_items if getattr(item, "artifact_id", None)
        }
        ws_ctx.chunks = [
            chunk
            for artifact_id in artifact_ids
            for chunk in chunks_by_artifact.get(artifact_id, [])
        ]
        if ws_ctx.evidence_items or ws_ctx.issues or ws_ctx.checklist_items or ws_ctx.chunks:
            ctx.workstreams[ws.value] = ws_ctx

    return ctx


def _format_titles(items: list[Any], *, limit: int = 3) -> str:
    if not items:
        return "None"
    return ", ".join(getattr(item, "title", "Untitled") for item in items[:limit])


def _format_issue_snapshot(items: list[Any], *, limit: int = 3) -> str:
    if not items:
        return "None"
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    ranked = sorted(
        items,
        key=lambda item: severity_order.get(getattr(item, "severity", "info"), 5),
    )
    lines = []
    for item in ranked[:limit]:
        lines.append(f"- [{item.severity}/{item.status}] {item.title}")
    return "\n".join(lines)


def _format_checklist_snapshot(items: list[Any], *, limit: int = 3) -> str:
    if not items:
        return "None"
    ordered = sorted(
        items,
        key=lambda item: (
            0 if getattr(item, "mandatory", False) else 1,
            0 if getattr(item, "status", "") != "done" else 1,
        ),
    )
    lines = []
    for item in ordered[:limit]:
        mandatory = "mandatory" if item.mandatory else "optional"
        lines.append(f"- [{item.status}] {item.title} ({mandatory})")
    return "\n".join(lines)


def _format_workstream_snapshot(ws_ctx: WorkstreamContext) -> str:
    linked_documents = len({chunk.artifact_id for chunk in ws_ctx.chunks})
    return "\n".join(
        [
            f"- Evidence items: {len(ws_ctx.evidence_items)}",
            f"- Linked document chunks: {len(ws_ctx.chunks)} across {linked_documents} documents",
            f"- Flagged issues: {len(ws_ctx.issues)}",
            f"- Checklist items: {len(ws_ctx.checklist_items)}",
            f"- Evidence preview: {_format_titles(ws_ctx.evidence_items)}",
            f"- Highest-priority issues:\n{_format_issue_snapshot(ws_ctx.issues)}",
            f"- Checklist focus:\n{_format_checklist_snapshot(ws_ctx.checklist_items)}",
        ]
    )


def _format_case_snapshot(case_ctx: CaseContext) -> str:
    lines = [
        f"- Documents uploaded: {case_ctx.document_count}",
        f"- Document chunks available to tools: {case_ctx.chunk_count}",
        f"- Active workstreams: {len(case_ctx.workstreams)}",
    ]
    for ws_domain, ws_ctx in case_ctx.workstreams.items():
        lines.append(
            f"- {ws_domain}: evidence={len(ws_ctx.evidence_items)}, "
            f"issues={len(ws_ctx.issues)}, checklist={len(ws_ctx.checklist_items)}, "
            f"chunks={len(ws_ctx.chunks)}"
        )
    return "\n".join(lines)


def _phase9_snapshot_block(
    legal_summary,
    tax_summary,
    compliance_summary,
) -> str:
    phase9_snapshot = format_phase9_snapshot(
        legal_summary=legal_summary,
        tax_summary=tax_summary,
        compliance_summary=compliance_summary,
    )
    return f"## Legal / Tax / Regulatory Snapshot\n{phase9_snapshot}\n\n"


def _phase10_snapshot_block(
    commercial_summary,
    operations_summary,
    cyber_summary,
    forensic_summary,
) -> str:
    phase10_snapshot = format_phase10_snapshot(
        commercial_summary=commercial_summary,
        operations_summary=operations_summary,
        cyber_summary=cyber_summary,
        forensic_summary=forensic_summary,
    )
    return f"## Commercial / Operations / Cyber / Forensic Snapshot\n{phase10_snapshot}\n\n"


def _phase11_snapshot_block(
    *,
    motion_pack: str,
    buy_side_analysis=None,
    borrower_scorecard=None,
    vendor_risk_tier=None,
) -> str:
    phase11_snapshot = format_phase11_snapshot(
        motion_pack=motion_pack,
        buy_side_analysis=buy_side_analysis,
        borrower_scorecard=borrower_scorecard,
        vendor_risk_tier=vendor_risk_tier,
    )
    return f"## Motion Pack Deepening Snapshot\n{phase11_snapshot}\n\n"


def _phase12_snapshot_block(
    *,
    sector_pack: str,
    tech_saas_metrics=None,
    manufacturing_metrics=None,
    bfsi_nbfc_metrics=None,
) -> str:
    phase12_snapshot = format_phase12_snapshot(
        sector_pack=sector_pack,
        tech_saas_metrics=tech_saas_metrics,
        manufacturing_metrics=manufacturing_metrics,
        bfsi_nbfc_metrics=bfsi_nbfc_metrics,
    )
    return f"## Sector Pack Deepening Snapshot\n{phase12_snapshot}\n\n"


def _build_llm(*, provider: str, model: str, api_key: str | None, base_url: str | None) -> LLM:
    """Create a CrewAI LLM instance from application settings."""
    model_prefix = {
        "openai": "openai",
        "anthropic": "anthropic",
        "openrouter": "openrouter",
    }
    prefix = model_prefix.get(provider, "openai")
    llm_kwargs = {
        "model": f"{prefix}/{model}",
        "api_key": api_key,
        "temperature": 0.2,
    }
    if provider == "openrouter":
        llm_kwargs["base_url"] = base_url or "https://openrouter.ai/api/v1"
    return LLM(**llm_kwargs)


def build_due_diligence_crew(
    case_ctx: CaseContext,
    settings,
    *,
    llm_provider: str | None = None,
    llm_model: str | None = None,
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
) -> tuple[Crew, dict[str, str], dict[str, list[Any]]]:
    """Build a CrewAI crew for the given case context."""
    resolved_provider = llm_provider or settings.llm_provider
    resolved_model = llm_model or settings.llm_model
    llm = _build_llm(
        provider=resolved_provider,
        model=resolved_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )
    motion_ctx = motion_pack_context(case_ctx.motion_pack)
    sector_ctx = sector_pack_context(case_ctx.sector_pack)

    preamble = (
        f"Case: {case_ctx.case_name}\n"
        f"Target: {case_ctx.target_name}\n"
        f"Country: {case_ctx.country}\n"
        f"Motion Pack: {case_ctx.motion_pack}\n"
        f"Sector Pack: {case_ctx.sector_pack}\n"
        f"Documents uploaded: {case_ctx.document_count}\n\n"
        f"{motion_ctx}\n{sector_ctx}"
    )

    agents: list[Agent] = []
    tasks: list[Task] = []
    task_map: dict[str, str] = {}
    tool_map: dict[str, list[Any]] = {}

    for ws_domain, ws_ctx in case_ctx.workstreams.items():
        agent_cfg = WORKSTREAM_AGENT_CONFIGS.get(ws_domain)
        if agent_cfg is None:
            continue

        tools = build_workstream_tools(
            workstream_domain=ws_domain,
            motion_pack=case_ctx.motion_pack,
            evidence_items=ws_ctx.evidence_items,
            issues=ws_ctx.issues,
            checklist_items=ws_ctx.checklist_items,
            chunk_items=ws_ctx.chunks,
            default_top_k=settings.crew_tool_top_k,
            max_usage_count=settings.crew_tool_max_usage,
            financial_summary=financial_summary,
            legal_summary=legal_summary,
            tax_summary=tax_summary,
            compliance_summary=compliance_summary,
            commercial_summary=commercial_summary,
            operations_summary=operations_summary,
            cyber_summary=cyber_summary,
            forensic_summary=forensic_summary,
            sector_pack=case_ctx.sector_pack,
            buy_side_analysis=buy_side_analysis,
            borrower_scorecard=borrower_scorecard,
            vendor_risk_tier=vendor_risk_tier,
            tech_saas_metrics=tech_saas_metrics,
            manufacturing_metrics=manufacturing_metrics,
            bfsi_nbfc_metrics=bfsi_nbfc_metrics,
        )
        agent = Agent(
            role=agent_cfg["role"],
            goal=agent_cfg["goal"],
            backstory=agent_cfg["backstory"],
            llm=llm,
            verbose=settings.crew_verbose,
            allow_delegation=False,
            max_iter=3,
            max_rpm=settings.crew_max_rpm,
            tools=tools,
            respect_context_window=True,
        )
        agents.append(agent)

        task_name = f"analyze_{ws_domain}"
        financial_block = (
            f"## Financial QoE Snapshot\n{format_financial_snapshot(financial_summary)}\n\n"
            if ws_domain == WorkstreamDomain.FINANCIAL_QOE.value
            else ""
        )
        phase9_block = (
            _phase9_snapshot_block(
                legal_summary,
                tax_summary,
                compliance_summary,
            )
            if ws_domain
            in {
                WorkstreamDomain.LEGAL_CORPORATE.value,
                WorkstreamDomain.TAX.value,
                WorkstreamDomain.REGULATORY.value,
            }
            else ""
        )
        phase10_block = (
            _phase10_snapshot_block(
                commercial_summary,
                operations_summary,
                cyber_summary,
                forensic_summary,
            )
            if ws_domain
            in {
                WorkstreamDomain.COMMERCIAL.value,
                WorkstreamDomain.OPERATIONS.value,
                WorkstreamDomain.CYBER_PRIVACY.value,
                WorkstreamDomain.FORENSIC_COMPLIANCE.value,
            }
            else ""
        )
        phase11_block = _phase11_snapshot_block(
            motion_pack=case_ctx.motion_pack,
            buy_side_analysis=buy_side_analysis,
            borrower_scorecard=borrower_scorecard,
            vendor_risk_tier=vendor_risk_tier,
        )
        phase12_block = _phase12_snapshot_block(
            sector_pack=case_ctx.sector_pack,
            tech_saas_metrics=tech_saas_metrics,
            manufacturing_metrics=manufacturing_metrics,
            bfsi_nbfc_metrics=bfsi_nbfc_metrics,
        )
        available_tools_block = f"## Available Tools\n{', '.join(tool.name for tool in tools)}\n\n"
        task = Task(
            name=task_name,
            description=(
                f"{preamble}\n\n"
                f"You own the {ws_domain.replace('_', ' ').title()} workstream.\n\n"
                "You are intentionally receiving a compact snapshot so you can stay "
                "within the context window. Use your read-only tools before you make "
                "material assertions.\n\n"
                "## Workstream Snapshot\n"
                f"{_format_workstream_snapshot(ws_ctx)}\n\n"
                + financial_block
                + phase9_block
                + phase10_block
                + phase11_block
                + phase12_block
                + available_tools_block
                + "Requirements:\n"
                "1. Ground material claims in the snapshot or tool results only.\n"
                "2. Use the evidence search tool when you need cited support.\n"
                "3. Use the issue and checklist tools to confirm blockers and open gaps.\n"
                "4. Do not invent facts that are absent from the case data."
            ),
            expected_output=(
                "A JSON object with: status (ready_for_review/needs_follow_up/blocked), "
                "headline, narrative, finding_count, blocker_count, confidence, "
                "recommended_next_action."
            ),
            agent=agent,
            output_pydantic=WorkstreamAnalysisOutput,
        )
        tasks.append(task)
        task_map[ws_domain] = task_name
        tool_map[ws_domain] = tools

    motion_pack_tools = build_case_tools(
        motion_pack=case_ctx.motion_pack,
        evidence_items=[
            evidence_item
            for ws_ctx in case_ctx.workstreams.values()
            for evidence_item in ws_ctx.evidence_items
        ],
        issues=[issue for ws_ctx in case_ctx.workstreams.values() for issue in ws_ctx.issues],
        checklist_items=[
            item for ws_ctx in case_ctx.workstreams.values() for item in ws_ctx.checklist_items
        ],
        chunk_items=case_ctx.chunks,
        default_top_k=settings.crew_tool_top_k,
        max_usage_count=settings.crew_tool_max_usage,
        financial_summary=financial_summary,
        legal_summary=legal_summary,
        tax_summary=tax_summary,
        compliance_summary=compliance_summary,
        commercial_summary=commercial_summary,
        operations_summary=operations_summary,
        cyber_summary=cyber_summary,
        forensic_summary=forensic_summary,
        sector_pack=case_ctx.sector_pack,
        buy_side_analysis=buy_side_analysis,
        borrower_scorecard=borrower_scorecard,
        vendor_risk_tier=vendor_risk_tier,
        tech_saas_metrics=tech_saas_metrics,
        manufacturing_metrics=manufacturing_metrics,
        bfsi_nbfc_metrics=bfsi_nbfc_metrics,
    )

    motion_pack_config = None
    motion_pack_prompt = None
    motion_pack_state_available = False
    if case_ctx.motion_pack == "buy_side_diligence":
        motion_pack_config = BUY_SIDE_SPECIALIST_CONFIG
        motion_pack_state_available = buy_side_analysis is not None
        motion_pack_prompt = build_buy_side_prompt(
            format_phase11_snapshot(
                motion_pack=case_ctx.motion_pack,
                buy_side_analysis=buy_side_analysis,
            )
        )
    elif case_ctx.motion_pack == "credit_lending":
        motion_pack_config = CREDIT_SPECIALIST_CONFIG
        motion_pack_state_available = borrower_scorecard is not None
        motion_pack_prompt = build_credit_prompt(
            format_phase11_snapshot(
                motion_pack=case_ctx.motion_pack,
                borrower_scorecard=borrower_scorecard,
            )
        )
    elif case_ctx.motion_pack == "vendor_onboarding":
        motion_pack_config = VENDOR_SPECIALIST_CONFIG
        motion_pack_state_available = vendor_risk_tier is not None
        motion_pack_prompt = build_vendor_prompt(
            format_phase11_snapshot(
                motion_pack=case_ctx.motion_pack,
                vendor_risk_tier=vendor_risk_tier,
            )
        )

    if (
        motion_pack_config is not None
        and motion_pack_prompt is not None
        and motion_pack_state_available
    ):
        motion_pack_agent = Agent(
            role=motion_pack_config["role"],
            goal=motion_pack_config["goal"],
            backstory=motion_pack_config["backstory"],
            llm=llm,
            verbose=settings.crew_verbose,
            allow_delegation=False,
            max_iter=3,
            max_rpm=settings.crew_max_rpm,
            tools=motion_pack_tools,
            respect_context_window=True,
        )
        agents.append(motion_pack_agent)
        tool_map["motion_pack_specialist"] = motion_pack_tools
        pack_task = Task(
            name="motion_pack_analysis",
            description=(
                f"{preamble}\n\n"
                f"{motion_pack_prompt}\n"
                "Requirements:\n"
                "1. Focus on the motion-pack specific outputs only.\n"
                "2. Use the relevant tool before making material assertions.\n"
                "3. Surface the top decision points for reviewers and approvers.\n"
                "4. Do not restate generic workstream analysis without tying it to the motion pack."
            ),
            expected_output=(
                "A JSON object with: status, headline, narrative, key_items, recommended_actions."
            ),
            agent=motion_pack_agent,
            output_pydantic=MotionPackAnalysisOutput,
        )
        tasks.append(pack_task)

    coordinator_tools = build_case_tools(
        motion_pack=case_ctx.motion_pack,
        evidence_items=[
            evidence_item
            for ws_ctx in case_ctx.workstreams.values()
            for evidence_item in ws_ctx.evidence_items
        ],
        issues=[issue for ws_ctx in case_ctx.workstreams.values() for issue in ws_ctx.issues],
        checklist_items=[
            item for ws_ctx in case_ctx.workstreams.values() for item in ws_ctx.checklist_items
        ],
        chunk_items=case_ctx.chunks,
        default_top_k=settings.crew_tool_top_k,
        max_usage_count=settings.crew_tool_max_usage,
        financial_summary=financial_summary,
        legal_summary=legal_summary,
        tax_summary=tax_summary,
        compliance_summary=compliance_summary,
        commercial_summary=commercial_summary,
        operations_summary=operations_summary,
        cyber_summary=cyber_summary,
        forensic_summary=forensic_summary,
        sector_pack=case_ctx.sector_pack,
        buy_side_analysis=buy_side_analysis,
        borrower_scorecard=borrower_scorecard,
        vendor_risk_tier=vendor_risk_tier,
        tech_saas_metrics=tech_saas_metrics,
        manufacturing_metrics=manufacturing_metrics,
        bfsi_nbfc_metrics=bfsi_nbfc_metrics,
    )
    coordinator = Agent(
        role=COORDINATOR_CONFIG["role"],
        goal=COORDINATOR_CONFIG["goal"],
        backstory=COORDINATOR_CONFIG["backstory"],
        llm=llm,
        verbose=settings.crew_verbose,
        allow_delegation=False,
        max_iter=3,
        max_rpm=settings.crew_max_rpm,
        tools=coordinator_tools,
        respect_context_window=True,
    )
    agents.append(coordinator)
    tool_map["coordinator"] = coordinator_tools
    coordinator_tools_block = (
        f"## Available Tools\n{', '.join(tool.name for tool in coordinator_tools)}\n\n"
    )

    summary_task = Task(
        name="executive_synthesis",
        description=(
            f"{preamble}\n\n"
            f"You have received analyses from {len(tasks)} workstream specialists. "
            f"Workstreams covered: {', '.join(case_ctx.workstreams.keys())}.\n\n"
            "## Case Snapshot\n"
            f"{_format_case_snapshot(case_ctx)}\n\n"
            "## Financial QoE Snapshot\n"
            f"{format_financial_snapshot(financial_summary)}\n\n"
            + _phase9_snapshot_block(
                legal_summary,
                tax_summary,
                compliance_summary,
            )
            + _phase10_snapshot_block(
                commercial_summary,
                operations_summary,
                cyber_summary,
                forensic_summary,
            )
            + _phase11_snapshot_block(
                motion_pack=case_ctx.motion_pack,
                buy_side_analysis=buy_side_analysis,
                borrower_scorecard=borrower_scorecard,
                vendor_risk_tier=vendor_risk_tier,
            )
            + _phase12_snapshot_block(
                sector_pack=case_ctx.sector_pack,
                tech_saas_metrics=tech_saas_metrics,
                manufacturing_metrics=manufacturing_metrics,
                bfsi_nbfc_metrics=bfsi_nbfc_metrics,
            )
            + coordinator_tools_block
            + "Synthesize the workstream findings into a cohesive executive summary. "
            "Use the case-wide tools if you need to validate the top risks or inspect "
            "underlying evidence before finalizing the recommendation."
        ),
        expected_output=(
            "A JSON object with: executive_summary, overall_risk_assessment "
            "(low/medium/high/critical), top_risks (list), recommended_next_steps (list)."
        ),
        agent=coordinator,
        context=tasks,
        output_pydantic=ExecutiveSummaryOutput,
    )
    tasks.append(summary_task)

    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=settings.crew_verbose,
        max_rpm=settings.crew_max_rpm,
    )

    return crew, task_map, tool_map


async def run_crew(crew: Crew, *, provider: str, model: str) -> Any:
    """Run crew.kickoff() in a thread to avoid blocking the async event loop."""
    with observe_llm_run(provider=provider, model=model):
        return await asyncio.to_thread(crew.kickoff)
