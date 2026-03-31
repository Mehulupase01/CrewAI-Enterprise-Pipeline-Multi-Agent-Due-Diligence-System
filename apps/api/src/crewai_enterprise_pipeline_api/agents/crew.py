"""CrewAI crew factory for due diligence workflow runs.

Builds a crew with one agent per active workstream + a coordinator,
then kicks off analysis and returns structured output.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from crewai import LLM, Agent, Crew, Process, Task

from crewai_enterprise_pipeline_api.agents.config import (
    COORDINATOR_CONFIG,
    WORKSTREAM_AGENT_CONFIGS,
    motion_pack_context,
    sector_pack_context,
)
from crewai_enterprise_pipeline_api.agents.models import (
    ExecutiveSummaryOutput,
    WorkstreamAnalysisOutput,
)
from crewai_enterprise_pipeline_api.domain.models import WorkstreamDomain

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Case context builder — formats case data into text for agent prompts
# ---------------------------------------------------------------------------


@dataclass
class WorkstreamContext:
    """Pre-loaded data for a single workstream."""

    domain: str
    evidence_items: list[Any] = field(default_factory=list)
    issues: list[Any] = field(default_factory=list)
    checklist_items: list[Any] = field(default_factory=list)


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
    workstreams: dict[str, WorkstreamContext] = field(default_factory=dict)


def build_case_context(case) -> CaseContext:
    """Build CaseContext from a loaded CaseRecord (with eager-loaded relations)."""
    ctx = CaseContext(
        case_id=case.id,
        case_name=case.name,
        target_name=case.target_name,
        country=case.country,
        motion_pack=case.motion_pack,
        sector_pack=case.sector_pack,
        document_count=len(case.documents),
    )

    for ws in WorkstreamDomain:
        ws_ctx = WorkstreamContext(domain=ws.value)
        ws_ctx.evidence_items = [
            e for e in case.evidence_items if e.workstream_domain == ws.value
        ]
        ws_ctx.issues = [
            i for i in case.issues if i.workstream_domain == ws.value
        ]
        ws_ctx.checklist_items = [
            c for c in case.checklist_items if c.workstream_domain == ws.value
        ]
        if ws_ctx.evidence_items or ws_ctx.issues or ws_ctx.checklist_items:
            ctx.workstreams[ws.value] = ws_ctx

    return ctx


def _format_evidence(items: list[Any]) -> str:
    if not items:
        return "No evidence items in this workstream."
    lines = []
    for e in items:
        lines.append(
            f"- [{e.evidence_kind}] {e.title} (confidence: {e.confidence:.2f})\n"
            f"  Citation: {e.citation}\n"
            f"  Excerpt: {e.excerpt[:300]}"
        )
    return "\n".join(lines)


def _format_issues(items: list[Any]) -> str:
    if not items:
        return "No issues flagged in this workstream."
    lines = []
    for i in items:
        lines.append(
            f"- [{i.severity}] {i.title} ({i.status})\n"
            f"  Impact: {i.business_impact}\n"
            f"  Action: {i.recommended_action or 'Triage pending'}"
        )
    return "\n".join(lines)


def _format_checklist(items: list[Any]) -> str:
    if not items:
        return "No checklist items in this workstream."
    lines = []
    for c in items:
        mandatory = "MANDATORY" if c.mandatory else "optional"
        lines.append(f"- [{c.status}] {c.title} ({mandatory}): {c.detail[:200]}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Crew builder
# ---------------------------------------------------------------------------


def _build_llm(settings) -> LLM:
    """Create a CrewAI LLM instance from application settings."""
    model_prefix = {
        "openai": "openai",
        "anthropic": "anthropic",
    }
    prefix = model_prefix.get(settings.llm_provider, "openai")
    return LLM(
        model=f"{prefix}/{settings.llm_model}",
        api_key=settings.llm_api_key,
        temperature=0.2,
    )


def build_due_diligence_crew(
    case_ctx: CaseContext,
    settings,
) -> tuple[Crew, dict[str, str]]:
    """Build a CrewAI crew for the given case context.

    Returns (crew, task_map) where task_map maps workstream_domain → task.name
    so callers can correlate outputs.
    """
    llm = _build_llm(settings)
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

    # One agent + task per active workstream
    for ws_domain, ws_ctx in case_ctx.workstreams.items():
        agent_cfg = WORKSTREAM_AGENT_CONFIGS.get(ws_domain)
        if agent_cfg is None:
            continue

        agent = Agent(
            role=agent_cfg["role"],
            goal=agent_cfg["goal"],
            backstory=agent_cfg["backstory"],
            llm=llm,
            verbose=settings.crew_verbose,
            allow_delegation=False,
            max_iter=3,
            max_rpm=settings.crew_max_rpm,
        )
        agents.append(agent)

        task_name = f"analyze_{ws_domain}"
        task = Task(
            name=task_name,
            description=(
                f"{preamble}\n\n"
                f"You are analyzing the **{ws_domain.replace('_', ' ').title()}** "
                f"workstream.\n\n"
                f"## Evidence Items ({len(ws_ctx.evidence_items)})\n"
                f"{_format_evidence(ws_ctx.evidence_items)}\n\n"
                f"## Flagged Issues ({len(ws_ctx.issues)})\n"
                f"{_format_issues(ws_ctx.issues)}\n\n"
                f"## Checklist Items ({len(ws_ctx.checklist_items)})\n"
                f"{_format_checklist(ws_ctx.checklist_items)}\n\n"
                f"Analyze all evidence, issues, and checklist items above. "
                f"Provide a structured assessment of this workstream."
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

    # Coordinator agent synthesizes all workstream findings
    coordinator = Agent(
        role=COORDINATOR_CONFIG["role"],
        goal=COORDINATOR_CONFIG["goal"],
        backstory=COORDINATOR_CONFIG["backstory"],
        llm=llm,
        verbose=settings.crew_verbose,
        allow_delegation=False,
        max_iter=3,
        max_rpm=settings.crew_max_rpm,
    )
    agents.append(coordinator)

    summary_task = Task(
        name="executive_synthesis",
        description=(
            f"{preamble}\n\n"
            f"You have received analyses from {len(tasks)} workstream specialists. "
            f"Workstreams covered: {', '.join(case_ctx.workstreams.keys())}.\n\n"
            f"Synthesize all workstream findings into a cohesive executive summary. "
            f"Identify the top risks across all workstreams, assess overall deal "
            f"readiness, and recommend concrete next steps."
        ),
        expected_output=(
            "A JSON object with: executive_summary, overall_risk_assessment "
            "(low/medium/high/critical), top_risks (list), recommended_next_steps (list)."
        ),
        agent=coordinator,
        context=tasks,  # receives all workstream task outputs
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

    return crew, task_map


async def run_crew(crew: Crew) -> Any:
    """Run crew.kickoff() in a thread to avoid blocking the async event loop."""
    return await asyncio.to_thread(crew.kickoff)
