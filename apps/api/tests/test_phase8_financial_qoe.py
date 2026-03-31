from __future__ import annotations

from unittest.mock import MagicMock

from crewai_enterprise_pipeline_api.domain.models import (
    FinancialMetricSummary,
    FinancialPeriod,
    WorkstreamDomain,
)
from crewai_enterprise_pipeline_api.evaluation.financial_fixtures import (
    build_financial_workbook_bytes,
)
from crewai_enterprise_pipeline_api.ingestion.financial_parser import FinancialParser


def test_financial_parser_extracts_structured_periods_from_xlsx() -> None:
    parser = FinancialParser()
    statement = parser.parse_document(
        artifact_id="artifact-1",
        artifact_title="Borrower financial workbook",
        document_kind="borrower_financial_pack",
        filename="borrower_financial_pack.xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        parser_name="openpyxl",
        content=build_financial_workbook_bytes(),
        fallback_text=None,
    )

    assert statement is not None
    assert len(statement.periods) == 4
    assert statement.periods[-1].label == "FY25"
    assert statement.periods[-1].revenue == 170.0
    assert statement.periods[-1].ebitda == 22.3
    assert statement.periods[-1].operating_cash_flow == -3.0
    assert statement.periods[-1].customer_concentration_top_3 == 0.72
    assert statement.periods[-1].q4_revenue_share == 0.45
    assert statement.qoe_adjustments[0].label == "One-time legal cost"
    assert statement.qoe_adjustments[0].amount == -2.5


def test_financial_summary_endpoint_computes_ratios_and_flags(client) -> None:
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Phase8 Finance",
            "target_name": "Finance Signals Private Limited",
            "summary": "Phase 8 financial QoE validation case.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case_response.json()["id"]

    seed_response = client.post(f"/api/v1/cases/{case_id}/checklist/seed")
    assert seed_response.status_code == 201

    upload_response = client.post(
        f"/api/v1/cases/{case_id}/documents/upload",
        data={
            "document_kind": "audited_financials",
            "source_kind": "uploaded_dataroom",
            "workstream_domain": "financial_qoe",
            "title": "Audited financial workbook",
            "evidence_kind": "metric",
        },
        files={
            "file": (
                "audited_financials.xlsx",
                build_financial_workbook_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert upload_response.status_code == 201

    summary_response = client.get(f"/api/v1/cases/{case_id}/financial-summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()

    assert len(summary["periods"]) == 4
    assert summary["normalized_ebitda"] == 24.8
    assert summary["ratios"]["revenue_cagr_3y"] == 0.1935
    assert summary["ratios"]["ebitda_margin"] == 0.1312
    assert summary["ratios"]["cash_conversion"] == -0.1345
    assert summary["ratios"]["debt_to_ebitda"] == 1.435
    assert summary["ratios"]["interest_coverage"] == 4.9556
    assert summary["ratios"]["working_capital_days"] == 60.1176
    assert any("top 3 customers" in flag.lower() for flag in summary["flags"])
    assert any("negative despite positive ebitda" in flag.lower() for flag in summary["flags"])
    assert any("q4 contributes more than 40%" in flag.lower() for flag in summary["flags"])
    assert {update["template_key"] for update in summary["checklist_updates"]} == {
        "financial_qoe.audited_financials"
    }


def test_credit_motion_pack_auto_satisfies_relevant_financial_checklist_items(client) -> None:
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Phase8 Credit",
            "target_name": "Credit Signals Private Limited",
            "summary": "Credit checklist auto-satisfaction validation case.",
            "motion_pack": "credit_lending",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case_response.json()["id"]

    seed_response = client.post(f"/api/v1/cases/{case_id}/checklist/seed")
    assert seed_response.status_code == 201

    upload_response = client.post(
        f"/api/v1/cases/{case_id}/documents/upload",
        data={
            "document_kind": "borrower_financial_pack",
            "source_kind": "uploaded_dataroom",
            "workstream_domain": "financial_qoe",
            "title": "Borrower financial workbook",
            "evidence_kind": "metric",
        },
        files={
            "file": (
                "borrower_financial_pack.xlsx",
                build_financial_workbook_bytes(bridge_variant="credit"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert upload_response.status_code == 201

    summary_response = client.get(f"/api/v1/cases/{case_id}/financial-summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()

    updated_keys = {update["template_key"] for update in summary["checklist_updates"]}
    assert {
        "financial_qoe.borrower_statements",
        "financial_qoe.debt_service_capacity",
        "financial_qoe.working_capital_behaviour",
    }.issubset(updated_keys)

    checklist_response = client.get(f"/api/v1/cases/{case_id}/checklist")
    assert checklist_response.status_code == 200
    statuses = {
        item["template_key"]: item["status"]
        for item in checklist_response.json()
        if item["template_key"]
    }
    assert statuses["financial_qoe.borrower_statements"] == "satisfied"
    assert statuses["financial_qoe.debt_service_capacity"] == "satisfied"
    assert statuses["financial_qoe.working_capital_behaviour"] == "satisfied"


def test_financial_tools_attach_to_financial_workstream_when_summary_exists() -> None:
    from crewai_enterprise_pipeline_api.agents.crew import (
        CaseContext,
        WorkstreamContext,
        build_due_diligence_crew,
    )

    summary = FinancialMetricSummary(
        case_id="case-1",
        statement_count=1,
        periods=[
            FinancialPeriod(
                label="FY24",
                revenue=150.0,
                ebitda=20.0,
                operating_cash_flow=13.0,
                net_debt=35.0,
                interest_expense=5.0,
                working_capital=24.0,
            ),
            FinancialPeriod(
                label="FY25",
                revenue=170.0,
                ebitda=22.3,
                operating_cash_flow=-3.0,
                net_debt=32.0,
                interest_expense=4.5,
                working_capital=28.0,
                customer_concentration_top_3=0.72,
                q4_revenue_share=0.45,
            ),
        ],
        ratios={
            "revenue_cagr_3y": 0.1935,
            "ebitda_margin": 0.1312,
            "cash_conversion": -0.1345,
            "debt_to_ebitda": 1.435,
        },
        normalized_ebitda=24.8,
        flags=["Revenue concentration: top 3 customers exceed 60% of the latest period."],
    )

    ctx = CaseContext(
        case_id="case-1",
        case_name="Phase 8 Crew",
        target_name="Crew Finance",
        country="India",
        motion_pack="buy_side_diligence",
        sector_pack="tech_saas_services",
        document_count=1,
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
    settings.crew_tool_top_k = 5
    settings.crew_tool_max_usage = 6

    _, _, tool_map = build_due_diligence_crew(ctx, settings, financial_summary=summary)

    financial_tool_names = {tool.name for tool in tool_map[WorkstreamDomain.FINANCIAL_QOE.value]}
    coordinator_tool_names = {tool.name for tool in tool_map["coordinator"]}
    assert "review_financial_ratios" in financial_tool_names
    assert "lookup_financial_benchmarks" in financial_tool_names
    assert "review_financial_ratios" in coordinator_tool_names


def test_workflow_run_persists_financial_refresh_trace_and_enriched_synthesis(client) -> None:
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Phase8 Run",
            "target_name": "Workflow Finance Private Limited",
            "summary": "Workflow QoE integration validation case.",
            "motion_pack": "credit_lending",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case_response.json()["id"]

    client.post(f"/api/v1/cases/{case_id}/checklist/seed")
    client.post(
        f"/api/v1/cases/{case_id}/documents/upload",
        data={
            "document_kind": "borrower_financial_pack",
            "source_kind": "uploaded_dataroom",
            "workstream_domain": "financial_qoe",
            "title": "Borrower financial workbook",
            "evidence_kind": "metric",
        },
        files={
            "file": (
                "borrower_financial_pack.xlsx",
                build_financial_workbook_bytes(bridge_variant="workflow"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    run_response = client.post(
        f"/api/v1/cases/{case_id}/runs",
        json={"requested_by": "phase8-runner"},
    )
    assert run_response.status_code == 201
    payload = run_response.json()

    trace_steps = {event["step_key"] for event in payload["run"]["trace_events"]}
    assert "financial_qoe_refresh" in trace_steps

    financial_synthesis = next(
        synthesis
        for synthesis in payload["run"]["workstream_syntheses"]
        if synthesis["workstream_domain"] == "financial_qoe"
    )
    assert "normalized EBITDA" in financial_synthesis["narrative"]
    assert "Revenue concentration" in financial_synthesis["narrative"]
