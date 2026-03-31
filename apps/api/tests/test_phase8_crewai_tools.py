"""Phase 8 tests: tool-grounded CrewAI workflow execution."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from crewai_enterprise_pipeline_api.agents.models import (
    ExecutiveSummaryOutput,
    WorkstreamAnalysisOutput,
)
from crewai_enterprise_pipeline_api.agents.tools import (
    build_case_tools,
    build_workstream_tools,
    summarize_tool_usage,
)
from crewai_enterprise_pipeline_api.domain.models import WorkstreamDomain


def test_workstream_evidence_tool_returns_grounded_hits() -> None:
    tools = build_workstream_tools(
        workstream_domain=WorkstreamDomain.TAX.value,
        evidence_items=[
            SimpleNamespace(
                id="ev-1",
                artifact_id="doc-1",
                title="GST demand notice",
                evidence_kind="regulatory_notice",
                citation="GST Notice 2025/17",
                excerpt="A GST demand of INR 18 lakh remains unpaid.",
                confidence=0.91,
            )
        ],
        issues=[],
        checklist_items=[],
        chunk_items=[
            SimpleNamespace(
                chunk_id="chunk-1",
                artifact_id="doc-1",
                document_title="Indirect tax pack",
                document_kind="tax_pack",
                source_kind="uploaded_dataroom",
                section_title="GST notices",
                page_number=4,
                text="The GST demand relates to a reconciliation gap for FY24.",
            )
        ],
        max_usage_count=6,
    )

    result = tools[0].run(query="gst demand", top_k=2)
    assert "GST demand notice" in result
    assert "Indirect tax pack" in result
    assert tools[0].current_usage_count == 1


def test_issue_and_checklist_tools_filter_correctly() -> None:
    tools = build_case_tools(
        evidence_items=[],
        issues=[
            SimpleNamespace(
                id="issue-1",
                title="Pending FEMA clarification",
                severity="high",
                status="open",
                business_impact="Could delay downstream approval.",
                recommended_action="Obtain counsel memo.",
            ),
            SimpleNamespace(
                id="issue-2",
                title="Minor filing typo",
                severity="low",
                status="closed",
                business_impact="Low impact.",
                recommended_action=None,
            ),
        ],
        checklist_items=[
            SimpleNamespace(
                id="cl-1",
                title="RBI approval copy",
                status="open",
                detail="Need certified copy of latest RBI approval.",
                mandatory=True,
                owner="Regulatory lead",
            ),
            SimpleNamespace(
                id="cl-2",
                title="Legacy policy deck",
                status="done",
                detail="Already uploaded.",
                mandatory=False,
                owner=None,
            ),
        ],
        chunk_items=[],
        max_usage_count=6,
    )

    issue_result = tools[1].run(severity="high", status="open", top_k=5)
    checklist_result = tools[2].run(mandatory_only=True, status="open", top_k=5)

    assert "Pending FEMA clarification" in issue_result
    assert "Minor filing typo" not in issue_result
    assert "RBI approval copy" in checklist_result
    assert "Legacy policy deck" not in checklist_result


def test_summarize_tool_usage_reports_latest_query() -> None:
    tools = build_case_tools(
        evidence_items=[],
        issues=[],
        checklist_items=[],
        chunk_items=[],
        max_usage_count=6,
    )
    tools[0].run(query="revenue concentration", top_k=3)
    summary = summarize_tool_usage(tools)
    assert "search_case_evidence x1" in summary
    assert "revenue concentration" in summary


def test_crewai_run_trace_includes_tool_usage(client) -> None:
    case = client.post(
        "/api/v1/cases",
        json={
            "name": "Phase 8 Trace",
            "target_name": "Trace Corp",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case.json()["id"]
    client.post(f"/api/v1/cases/{case_id}/checklist/seed")

    from crewai_enterprise_pipeline_api.agents.crew import CaseContext, WorkstreamContext

    case_ctx = CaseContext(
        case_id=case_id,
        case_name="Phase 8 Trace",
        target_name="Trace Corp",
        country="India",
        motion_pack="buy_side_diligence",
        sector_pack="tech_saas_services",
        document_count=1,
        workstreams={
            WorkstreamDomain.FINANCIAL_QOE.value: WorkstreamContext(
                domain=WorkstreamDomain.FINANCIAL_QOE.value
            )
        },
    )

    tool_map = {
        WorkstreamDomain.FINANCIAL_QOE.value: build_workstream_tools(
            workstream_domain=WorkstreamDomain.FINANCIAL_QOE.value,
            evidence_items=[],
            issues=[],
            checklist_items=[],
            chunk_items=[],
            max_usage_count=6,
        ),
        "coordinator": build_case_tools(
            evidence_items=[],
            issues=[],
            checklist_items=[],
            chunk_items=[],
            max_usage_count=6,
        ),
    }
    tool_map[WorkstreamDomain.FINANCIAL_QOE.value][0].run(query="revenue", top_k=1)
    tool_map["coordinator"][0].run(query="top risks", top_k=1)

    fake_output = SimpleNamespace(
        tasks_output=[
            SimpleNamespace(
                name="analyze_financial_qoe",
                pydantic=WorkstreamAnalysisOutput(
                    status="ready_for_review",
                    headline="Financial workstream grounded by evidence search.",
                    narrative="Evidence review is sufficient for analyst sign-off.",
                    finding_count=2,
                    blocker_count=0,
                    confidence=0.81,
                    recommended_next_action="Review with finance lead.",
                ),
                raw="financial raw",
            ),
            SimpleNamespace(
                name="executive_synthesis",
                pydantic=ExecutiveSummaryOutput(
                    executive_summary="Overall case risk is manageable with follow-up.",
                    overall_risk_assessment="medium",
                    top_risks=["Revenue concentration"],
                    recommended_next_steps=["Validate customer contracts"],
                ),
                raw="summary raw",
            ),
        ],
        pydantic=ExecutiveSummaryOutput(
            executive_summary="Overall case risk is manageable with follow-up.",
            overall_risk_assessment="medium",
            top_risks=["Revenue concentration"],
            recommended_next_steps=["Validate customer contracts"],
        ),
        raw="summary raw",
    )

    with (
        patch(
            "crewai_enterprise_pipeline_api.services.workflow_service.WorkflowService._crew_available",
            return_value=True,
        ),
        patch(
            "crewai_enterprise_pipeline_api.agents.crew.build_case_context",
            return_value=case_ctx,
        ),
        patch(
            "crewai_enterprise_pipeline_api.agents.crew.build_due_diligence_crew",
            return_value=(MagicMock(), {"financial_qoe": "analyze_financial_qoe"}, tool_map),
        ),
        patch(
            "crewai_enterprise_pipeline_api.agents.crew.run_crew",
            new=AsyncMock(return_value=fake_output),
        ),
    ):
        response = client.post(
            f"/api/v1/cases/{case_id}/runs",
            json={"requested_by": "phase8-tester"},
        )

    assert response.status_code == 201
    payload = response.json()
    trace_messages = {
        item["step_key"]: item["message"] for item in payload["run"]["trace_events"]
    }
    assert "search_financial_qoe_evidence x1" in trace_messages["agent_financial_qoe"]
    assert "search_case_evidence x1" in trace_messages["coordinator_synthesis"]
    assert "Tool calls recorded: 2" in trace_messages["report_bundle_generation"]
