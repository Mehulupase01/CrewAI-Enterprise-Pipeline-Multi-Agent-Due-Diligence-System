from __future__ import annotations

from unittest.mock import MagicMock

from crewai_enterprise_pipeline_api.domain.models import (
    ArrWaterfallItem,
    TechSaasMetricsSummary,
)

TECH_COMMERCIAL_TEXT = (
    "Beginning ARR 90.0. New ARR 25.0. Expansion ARR 18.0. Contraction ARR 6.0. "
    "Churned ARR 7.0. Ending ARR 120.0. MRR 10.0. Net revenue retention 118%. "
    "Gross churn 4%. CAC 1.8. LTV 9.0. CAC payback 7 months. "
    "Top customer contributes 42 percent of ARR."
)

TECH_OPERATIONS_TEXT = (
    "Implementation remains founder dependent and a named delivery lead approves migration "
    "cutovers. Shared services tooling still supports two major enterprise implementations."
)

TECH_CYBER_TEXT = (
    "Consent mechanism implemented and privacy controls documented. "
    "ISO 27001 certified but no SOC 2 report is currently available."
)

MANUFACTURING_OPERATIONS_TEXT = (
    "Capacity utilization 78%. DIO 74 days. DSO 61 days. DPO 39 days. "
    "Asset turnover 1.85. CNC Line A WDV 12.0 replacement cost 16.5. "
    "Paint Shop WDV 8.0 replacement cost 10.0. Top 3 suppliers account for 58 percent of spend."
)

MANUFACTURING_REGULATORY_TEXT = (
    "Pollution control board consent renewal pending and hazardous-waste manifest "
    "reconciliation remains partially complete."
)

MANUFACTURING_FORENSIC_TEXT = (
    "Related-party procurement from a promoter-linked fabrication vendor was noted during the "
    "capex review."
)

MANUFACTURING_COMMERCIAL_TEXT = (
    "Order book remains concentrated in the top two OEM customers and dealer discount pressure "
    "is rising in the export segment."
)

BFSI_FINANCIAL_TEXT = (
    "GNPA 6.2%. NNPA 2.9%. CRAR 18.4%. ALM mismatch 12%. PSL compliance met target. "
    "1-30 days bucket 9%. 31-60 days bucket 6%."
)

BFSI_REGULATORY_TEXT = (
    "RBI registration remains current and prudential returns were filed on time."
)

BFSI_OPERATIONS_TEXT = (
    "Collections overrides still depend on a zonal credit head and manual exception approval "
    "remains active."
)

BFSI_CYBER_TEXT = (
    "KYC and AML controls are documented, but borrower-data access review remains partially "
    "complete."
)

BFSI_FORENSIC_TEXT = (
    "Connected lending and loan evergreening signals were reviewed in related-party borrower "
    "clusters."
)


def _create_case(client, *, sector_pack: str, motion_pack: str = "buy_side_diligence") -> str:
    response = client.post(
        "/api/v1/cases",
        json={
            "name": f"Project Phase12 {sector_pack}",
            "target_name": "Phase12 Systems Private Limited",
            "summary": "Phase 12 sector-pack deepening validation case.",
            "motion_pack": motion_pack,
            "sector_pack": sector_pack,
            "country": "India",
        },
    )
    assert response.status_code == 201
    case_id = response.json()["id"]
    seed_response = client.post(f"/api/v1/cases/{case_id}/checklist/seed")
    assert seed_response.status_code == 201
    return case_id


def _upload_text_document(
    client,
    case_id: str,
    *,
    title: str,
    filename: str,
    content: str,
    document_kind: str,
    workstream_domain: str,
    evidence_kind: str = "fact",
) -> None:
    response = client.post(
        f"/api/v1/cases/{case_id}/documents/upload",
        data={
            "document_kind": document_kind,
            "source_kind": "uploaded_dataroom",
            "workstream_domain": workstream_domain,
            "title": title,
            "evidence_kind": evidence_kind,
        },
        files={"file": (filename, content.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 201


def test_tech_saas_metrics_endpoint_returns_structured_metrics_and_updates_checklist(
    client,
) -> None:
    case_id = _create_case(client, sector_pack="tech_saas_services")
    _upload_text_document(
        client,
        case_id,
        title="SaaS metrics pack",
        filename="saas_metrics_pack.txt",
        content=TECH_COMMERCIAL_TEXT,
        document_kind="saas_metrics_pack",
        workstream_domain="commercial",
        evidence_kind="metric",
    )
    _upload_text_document(
        client,
        case_id,
        title="Delivery model review",
        filename="delivery_model_review.txt",
        content=TECH_OPERATIONS_TEXT,
        document_kind="delivery_model_review",
        workstream_domain="operations",
        evidence_kind="risk",
    )
    _upload_text_document(
        client,
        case_id,
        title="Security assurance memo",
        filename="security_assurance_memo.txt",
        content=TECH_CYBER_TEXT,
        document_kind="security_assurance_memo",
        workstream_domain="cyber_privacy",
        evidence_kind="risk",
    )

    response = client.get(f"/api/v1/cases/{case_id}/tech-saas-metrics")
    assert response.status_code == 200
    payload = response.json()

    assert payload["arr"] == 120.0
    assert payload["mrr"] == 10.0
    assert payload["nrr"] == 1.18
    assert payload["churn_rate"] == 0.04
    assert payload["payback_months"] == 7.0
    assert len(payload["arr_waterfall"]) >= 5
    assert any("SOC 2" in flag for flag in payload["flags"])
    assert {update["template_key"] for update in payload["checklist_updates"]} == {
        "commercial.customer_concentration",
        "operations.delivery_model",
        "cyber.privacy_controls",
    }


def test_manufacturing_metrics_endpoint_returns_structured_metrics_and_updates_checklist(
    client,
) -> None:
    case_id = _create_case(client, sector_pack="manufacturing_industrials")
    _upload_text_document(
        client,
        case_id,
        title="Plant operating review",
        filename="plant_operating_review.txt",
        content=MANUFACTURING_OPERATIONS_TEXT,
        document_kind="plant_operating_review",
        workstream_domain="operations",
        evidence_kind="metric",
    )
    _upload_text_document(
        client,
        case_id,
        title="EHS compliance review",
        filename="ehs_compliance_review.txt",
        content=MANUFACTURING_REGULATORY_TEXT,
        document_kind="ehs_compliance_review",
        workstream_domain="regulatory",
        evidence_kind="risk",
    )
    _upload_text_document(
        client,
        case_id,
        title="Procurement integrity note",
        filename="procurement_integrity_note.txt",
        content=MANUFACTURING_FORENSIC_TEXT,
        document_kind="procurement_integrity_note",
        workstream_domain="forensic_compliance",
        evidence_kind="risk",
    )
    _upload_text_document(
        client,
        case_id,
        title="Order book summary",
        filename="order_book_summary.txt",
        content=MANUFACTURING_COMMERCIAL_TEXT,
        document_kind="order_book_summary",
        workstream_domain="commercial",
        evidence_kind="risk",
    )

    response = client.get(f"/api/v1/cases/{case_id}/manufacturing-metrics")
    assert response.status_code == 200
    payload = response.json()

    assert payload["capacity_utilization"] == 0.78
    assert payload["dio"] == 74.0
    assert payload["dso"] == 61.0
    assert payload["dpo"] == 39.0
    assert payload["asset_turnover"] == 1.85
    assert len(payload["asset_register"]) == 2
    assert any("EHS/factory" in flag for flag in payload["flags"])
    assert len(payload["checklist_updates"]) == 6


def test_bfsi_nbfc_metrics_endpoint_returns_structured_metrics_and_updates_checklist(
    client,
) -> None:
    case_id = _create_case(client, sector_pack="bfsi_nbfc", motion_pack="credit_lending")
    _upload_text_document(
        client,
        case_id,
        title="NBFC portfolio monitor",
        filename="nbfc_portfolio_monitor.txt",
        content=BFSI_FINANCIAL_TEXT,
        document_kind="nbfc_portfolio_monitor",
        workstream_domain="financial_qoe",
        evidence_kind="metric",
    )
    _upload_text_document(
        client,
        case_id,
        title="RBI returns note",
        filename="rbi_returns_note.txt",
        content=BFSI_REGULATORY_TEXT,
        document_kind="rbi_returns_note",
        workstream_domain="regulatory",
        evidence_kind="fact",
    )
    _upload_text_document(
        client,
        case_id,
        title="Collections governance review",
        filename="collections_governance_review.txt",
        content=BFSI_OPERATIONS_TEXT,
        document_kind="collections_governance_review",
        workstream_domain="operations",
        evidence_kind="risk",
    )
    _upload_text_document(
        client,
        case_id,
        title="KYC AML controls note",
        filename="kyc_aml_controls_note.txt",
        content=BFSI_CYBER_TEXT,
        document_kind="kyc_aml_controls_note",
        workstream_domain="cyber_privacy",
        evidence_kind="risk",
    )
    _upload_text_document(
        client,
        case_id,
        title="Connected lending review",
        filename="connected_lending_review.txt",
        content=BFSI_FORENSIC_TEXT,
        document_kind="connected_lending_review",
        workstream_domain="forensic_compliance",
        evidence_kind="risk",
    )

    response = client.get(f"/api/v1/cases/{case_id}/bfsi-nbfc-metrics")
    assert response.status_code == 200
    payload = response.json()

    assert payload["gnpa"] == 0.062
    assert payload["nnpa"] == 0.029
    assert payload["crar"] == 0.184
    assert payload["alm_mismatch"] == 0.12
    assert payload["psl_compliance"] == "compliant"
    assert len(payload["alm_bucket_gaps"]) == 2
    assert any("GNPA exceeds 5%" in flag for flag in payload["flags"])
    assert len(payload["checklist_updates"]) == 6


def test_phase12_sector_tools_attach_to_the_crew_when_structured_state_exists() -> None:
    from crewai_enterprise_pipeline_api.agents.crew import (
        CaseContext,
        WorkstreamContext,
        build_due_diligence_crew,
    )

    ctx = CaseContext(
        case_id="case-1",
        case_name="Phase 12 Crew",
        target_name="Crew Sector Pack",
        country="India",
        motion_pack="buy_side_diligence",
        sector_pack="tech_saas_services",
        document_count=3,
        workstreams={
            "commercial": WorkstreamContext(domain="commercial"),
            "operations": WorkstreamContext(domain="operations"),
            "cyber_privacy": WorkstreamContext(domain="cyber_privacy"),
        },
    )
    tech_saas_metrics = TechSaasMetricsSummary(
        case_id="case-1",
        arr=120.0,
        mrr=10.0,
        nrr=1.18,
        churn_rate=0.04,
        ltv=9.0,
        cac=1.8,
        payback_months=7.0,
        arr_waterfall=[
            ArrWaterfallItem(label="New ARR", amount=25.0, note="New logo bookings."),
        ],
        flags=["SOC 2 evidence is absent for a SaaS-style delivery model."],
    )

    settings = MagicMock()
    settings.llm_provider = "openai"
    settings.llm_api_key = "test-key"
    settings.llm_model = "gpt-4o-mini"
    settings.crew_verbose = False
    settings.crew_max_rpm = 10
    settings.crew_tool_top_k = 5
    settings.crew_tool_max_usage = 6

    crew, _, tool_map = build_due_diligence_crew(
        ctx,
        settings,
        tech_saas_metrics=tech_saas_metrics,
    )

    assert len(crew.agents) == 4
    assert "review_tech_saas_metrics" in {tool.name for tool in tool_map["coordinator"]}
    assert "review_tech_saas_metrics" in {tool.name for tool in tool_map["commercial"]}


def test_workflow_run_persists_phase12_refresh_and_sector_pack_highlights(client) -> None:
    case_id = _create_case(client, sector_pack="tech_saas_services")
    _upload_text_document(
        client,
        case_id,
        title="SaaS metrics pack",
        filename="saas_metrics_pack.txt",
        content=TECH_COMMERCIAL_TEXT,
        document_kind="saas_metrics_pack",
        workstream_domain="commercial",
        evidence_kind="metric",
    )
    _upload_text_document(
        client,
        case_id,
        title="Delivery model review",
        filename="delivery_model_review.txt",
        content=TECH_OPERATIONS_TEXT,
        document_kind="delivery_model_review",
        workstream_domain="operations",
        evidence_kind="risk",
    )
    _upload_text_document(
        client,
        case_id,
        title="Security assurance memo",
        filename="security_assurance_memo.txt",
        content=TECH_CYBER_TEXT,
        document_kind="security_assurance_memo",
        workstream_domain="cyber_privacy",
        evidence_kind="risk",
    )

    run_response = client.post(
        f"/api/v1/cases/{case_id}/runs",
        json={"requested_by": "phase12-runner"},
    )
    assert run_response.status_code == 201
    payload = run_response.json()

    trace_steps = {event["step_key"] for event in payload["run"]["trace_events"]}
    assert "sector_pack_deepening_refresh" in trace_steps

    syntheses = {
        synthesis["workstream_domain"]: synthesis
        for synthesis in payload["run"]["workstream_syntheses"]
    }
    assert "Phase 12 Tech/SaaS deepening" in syntheses["commercial"]["narrative"]
    assert payload["executive_memo"]["sector_pack_highlights"]
    assert "Phase 12 Tech/SaaS deepening extracted" in payload["executive_memo"][
        "executive_summary"
    ]
