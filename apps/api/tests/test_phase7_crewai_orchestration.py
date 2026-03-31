"""Phase 7 tests: CrewAI multi-agent orchestration.

Tests cover:
- Agent config completeness (all 9 workstreams defined)
- Case context builder
- Crew construction
- Deterministic fallback when LLM_PROVIDER=none (AD-001)
- Output model validation
- Workstream status normalization
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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
from crewai_enterprise_pipeline_api.domain.models import (
    MotionPack,
    SectorPack,
    WorkstreamDomain,
)

# ---------------------------------------------------------------------------
# 1. Agent config completeness
# ---------------------------------------------------------------------------


def test_all_workstreams_have_agent_config() -> None:
    """Every WorkstreamDomain must have a corresponding agent config."""
    for ws in WorkstreamDomain:
        assert ws.value in WORKSTREAM_AGENT_CONFIGS, (
            f"Missing agent config for workstream: {ws.value}"
        )
        cfg = WORKSTREAM_AGENT_CONFIGS[ws.value]
        assert "role" in cfg and len(cfg["role"]) > 10
        assert "goal" in cfg and len(cfg["goal"]) > 20
        assert "backstory" in cfg and len(cfg["backstory"]) > 20


def test_coordinator_config_present() -> None:
    """Coordinator agent config must be defined."""
    assert "role" in COORDINATOR_CONFIG
    assert "goal" in COORDINATOR_CONFIG
    assert "backstory" in COORDINATOR_CONFIG


def test_motion_pack_contexts() -> None:
    """Every MotionPack must have a context string."""
    for mp in MotionPack:
        ctx = motion_pack_context(mp.value)
        assert len(ctx) > 20, f"Motion pack context too short for {mp.value}"


def test_sector_pack_contexts() -> None:
    """Every SectorPack must have a context string."""
    for sp in SectorPack:
        ctx = sector_pack_context(sp.value)
        assert len(ctx) > 20, f"Sector pack context too short for {sp.value}"


# ---------------------------------------------------------------------------
# 2. Output model validation
# ---------------------------------------------------------------------------


def test_workstream_analysis_output_valid() -> None:
    """WorkstreamAnalysisOutput round-trips correctly."""
    output = WorkstreamAnalysisOutput(
        status="needs_follow_up",
        headline="Tax exposure requires quantification.",
        narrative="The tax workstream has 3 open items...",
        finding_count=5,
        blocker_count=1,
        confidence=0.72,
        recommended_next_action="Obtain latest GST reconciliation.",
    )
    data = output.model_dump()
    assert data["status"] == "needs_follow_up"
    assert data["finding_count"] == 5
    assert data["confidence"] == 0.72


def test_executive_summary_output_valid() -> None:
    """ExecutiveSummaryOutput round-trips correctly."""
    output = ExecutiveSummaryOutput(
        executive_summary="The target shows moderate risk...",
        overall_risk_assessment="medium",
        top_risks=["Tax exposure", "Key-person dependency"],
        recommended_next_steps=["Resolve tax items", "Negotiate key-man insurance"],
    )
    data = output.model_dump()
    assert data["overall_risk_assessment"] == "medium"
    assert len(data["top_risks"]) == 2


# ---------------------------------------------------------------------------
# 3. Case context builder
# ---------------------------------------------------------------------------


def test_case_context_builder() -> None:
    """build_case_context creates WorkstreamContexts for populated workstreams only."""
    from crewai_enterprise_pipeline_api.agents.crew import build_case_context

    mock_case = MagicMock()
    mock_case.id = "case-001"
    mock_case.name = "Test Case"
    mock_case.target_name = "Target Corp"
    mock_case.country = "India"
    mock_case.motion_pack = "buy_side_diligence"
    mock_case.sector_pack = "tech_saas_services"
    mock_case.documents = [MagicMock()]

    # One evidence item in financial_qoe, one issue in legal_corporate
    ev = MagicMock()
    ev.workstream_domain = "financial_qoe"
    issue = MagicMock()
    issue.workstream_domain = "legal_corporate"
    cl = MagicMock()
    cl.workstream_domain = "financial_qoe"

    mock_case.evidence_items = [ev]
    mock_case.issues = [issue]
    mock_case.checklist_items = [cl]

    ctx = build_case_context(mock_case)
    assert ctx.case_name == "Test Case"
    assert ctx.document_count == 1
    assert "financial_qoe" in ctx.workstreams
    assert "legal_corporate" in ctx.workstreams
    # Workstreams with no data should not be present
    assert "hr" not in ctx.workstreams
    assert len(ctx.workstreams["financial_qoe"].evidence_items) == 1
    assert len(ctx.workstreams["legal_corporate"].issues) == 1


# ---------------------------------------------------------------------------
# 4. Deterministic fallback (AD-001)
# ---------------------------------------------------------------------------


def test_deterministic_fallback_when_no_llm(client) -> None:
    """When LLM_PROVIDER=none, execute_run uses deterministic path (no CrewAI)."""
    case = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Deterministic",
            "target_name": "Fallback Corp",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case.json()["id"]
    client.post(f"/api/v1/cases/{case_id}/checklist/seed")

    run = client.post(
        f"/api/v1/cases/{case_id}/runs",
        json={"requested_by": "test-operator"},
    )
    assert run.status_code == 201
    data = run.json()
    assert data["run"]["status"] == "completed"
    # Deterministic runs have the standard trace events
    step_keys = [e["step_key"] for e in data["run"]["trace_events"]]
    assert "case_snapshot" in step_keys
    assert "report_bundle_generation" in step_keys
    # CrewAI-specific events should NOT be present
    assert "crew_initialized" not in step_keys


# ---------------------------------------------------------------------------
# 5. Workstream status normalization
# ---------------------------------------------------------------------------


def test_status_normalization() -> None:
    """_normalize_ws_status handles various LLM-produced status strings."""
    from crewai_enterprise_pipeline_api.services.workflow_service import WorkflowService

    assert WorkflowService._normalize_ws_status("ready_for_review") == "ready_for_review"
    assert WorkflowService._normalize_ws_status("BLOCKED") == "blocked"
    assert WorkflowService._normalize_ws_status("Needs Follow-Up") == "needs_follow_up"
    assert WorkflowService._normalize_ws_status("needs follow up") == "needs_follow_up"
    assert WorkflowService._normalize_ws_status("blocked by issues") == "blocked"
    assert WorkflowService._normalize_ws_status("unknown-status") == "ready_for_review"


# ---------------------------------------------------------------------------
# 6. Crew building (unit test, no LLM call)
# ---------------------------------------------------------------------------


def test_crew_build_structure() -> None:
    """build_due_diligence_crew creates correct number of agents and tasks."""
    from crewai_enterprise_pipeline_api.agents.crew import (
        CaseContext,
        WorkstreamContext,
        build_due_diligence_crew,
    )

    ctx = CaseContext(
        case_id="c1",
        case_name="Test",
        target_name="Target",
        country="India",
        motion_pack="buy_side_diligence",
        sector_pack="tech_saas_services",
        document_count=3,
        workstreams={
            "financial_qoe": WorkstreamContext(domain="financial_qoe"),
            "legal_corporate": WorkstreamContext(domain="legal_corporate"),
        },
    )

    settings = MagicMock()
    settings.llm_provider = "openai"
    settings.llm_api_key = "test-key"
    settings.llm_model = "gpt-4o-mini"
    settings.crew_verbose = False
    settings.crew_max_rpm = 10

    crew, task_map = build_due_diligence_crew(ctx, settings)
    # 2 workstream agents + 1 coordinator = 3 agents
    assert len(crew.agents) == 3
    # 2 workstream tasks + 1 summary task = 3 tasks
    assert len(crew.tasks) == 3
    assert "financial_qoe" in task_map
    assert "legal_corporate" in task_map


# ---------------------------------------------------------------------------
# 7. Settings
# ---------------------------------------------------------------------------


def test_llm_settings_defaults() -> None:
    """LLM settings default to safe values (no LLM active)."""
    with patch.dict(
        "os.environ",
        {"DATABASE_URL": "sqlite+aiosqlite:///test.db", "APP_ENV": "test"},
    ):
        from crewai_enterprise_pipeline_api.core.settings import Settings

        s = Settings()
        assert s.llm_provider == "none"
        assert s.llm_api_key is None
        assert s.crew_verbose is False


# ---------------------------------------------------------------------------
# 8. Crew availability check
# ---------------------------------------------------------------------------


def test_crew_available_false_when_no_key(client) -> None:
    """_crew_available returns False when LLM_PROVIDER=none."""
    from crewai_enterprise_pipeline_api.services.workflow_service import WorkflowService

    ws = WorkflowService.__new__(WorkflowService)
    assert ws._crew_available() is False
