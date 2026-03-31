from __future__ import annotations

from unittest.mock import MagicMock

from crewai_enterprise_pipeline_api.domain.models import (
    BuySideAnalysis,
    FlagSeverity,
    PmiRiskItem,
    SpaIssueItem,
    ValuationBridgeItem,
)
from crewai_enterprise_pipeline_api.evaluation.financial_fixtures import (
    build_financial_workbook_bytes,
)

COMMERCIAL_TEXT = (
    "Top customer contributes 70 percent of ARR and renewal due next quarter. "
    "Net revenue retention remained at 118 percent while customer churn stayed at 4 percent. "
    "Pricing pressure increased after a discount requested by the top customer."
)

OPERATIONS_TEXT = (
    "Top 3 suppliers account for 65 percent of raw material spend. "
    "A single plant handles all capacity and maintenance backlog remains visible. "
    "The business is founder dependent and the single plant head approves procurement."
)

CYBER_TEXT = (
    "Consent mechanism implemented and purpose limitation documented. "
    "Retention policy approved and breach notification procedure tested. "
    "Significant data fiduciary registration pending. "
    "ISO 27001 certified but no SOC 2 yet. "
    "A security incident involving unauthorized access was reported last year."
)

FORENSIC_TEXT = (
    "Related party sales to a promoter-linked group company were identified. "
    "A common director appears across the buyer and vendor entities. "
    "Round tripping and fund diversion concerns were flagged in the bank trail. "
    "Revenue recognition used a bill and hold side letter. "
    "A litigation claim remains pending."
)

MCA_SECRETARIAL_TEXT = (
    "MCA annual return filed and charge register current. "
    "Ananya Sharma DIN 01234567. "
    "Rohan Mehta DIN 07654321. "
    "Promoter shareholding 62.5% and Public shareholding 37.5%. "
    "Wholly owned subsidiary: Meridian Payments Private Limited. "
    "A current charge in favour of Axis Bank remains registered."
)

CUSTOMER_MSA_TEXT = (
    "This Master Services Agreement may terminate upon a change of control. "
    "Assignment requires prior written consent. "
    "Either party may terminate for material breach. "
    "The supplier will indemnify the customer for third-party claims. "
    "Aggregate liability cap equals fees paid in the prior twelve months. "
    "This agreement is governed by the laws of India and subject to the "
    "jurisdiction of Mumbai courts."
)

TAX_STATUTORY_TEXT = (
    "GSTIN 27ABCDE1234F1Z5 remains active and current. "
    "GST returns filed on time. Income tax return current. "
    "TDS and payroll compliance current. "
    "Transfer pricing study current and arm's length. "
    "Deferred tax asset schedule current and compliant."
)

VENDOR_REGULATORY_TEXT = (
    "Vendor registration remains current. "
    "No sanctions hits were detected. "
    "No licensing restriction was identified for the proposed scope."
)

COVENANT_MONITORING_TEXT = (
    "The borrower breached a covenant in Q4 and debt service coverage fell below the internal "
    "threshold. Waiver pending. Days past due moved to 38."
)


def _create_case(
    client,
    *,
    motion_pack: str,
    sector_pack: str = "tech_saas_services",
) -> str:
    response = client.post(
        "/api/v1/cases",
        json={
            "name": f"Project Phase11 {motion_pack}",
            "target_name": "Phase11 Signals Private Limited",
            "summary": "Phase 11 motion-pack deepening validation case.",
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
        files={
            "file": (
                filename,
                content.encode("utf-8"),
                "text/plain",
            )
        },
    )
    assert response.status_code == 201


def _upload_financial_workbook(
    client,
    case_id: str,
    *,
    title: str,
    filename: str,
    document_kind: str,
    bridge_variant: str = "default",
) -> None:
    response = client.post(
        f"/api/v1/cases/{case_id}/documents/upload",
        data={
            "document_kind": document_kind,
            "source_kind": "uploaded_dataroom",
            "workstream_domain": "financial_qoe",
            "title": title,
            "evidence_kind": "metric",
        },
        files={
            "file": (
                filename,
                build_financial_workbook_bytes(bridge_variant=bridge_variant),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 201


def test_buy_side_analysis_endpoint_returns_structured_outputs_and_checklist_updates(
    client,
) -> None:
    case_id = _create_case(client, motion_pack="buy_side_diligence")
    _upload_financial_workbook(
        client,
        case_id,
        title="Audited financial workbook",
        filename="audited_financials.xlsx",
        document_kind="audited_financials",
        bridge_variant="workflow",
    )
    _upload_text_document(
        client,
        case_id,
        title="MCA secretarial summary",
        filename="mca_secretarial_summary.txt",
        content=MCA_SECRETARIAL_TEXT,
        document_kind="mca_secretarial_summary",
        workstream_domain="legal_corporate",
    )
    _upload_text_document(
        client,
        case_id,
        title="Enterprise customer MSA",
        filename="enterprise_customer_msa.txt",
        content=CUSTOMER_MSA_TEXT,
        document_kind="customer_msa",
        workstream_domain="legal_corporate",
        evidence_kind="contract",
    )
    _upload_text_document(
        client,
        case_id,
        title="Tax statutory note",
        filename="tax_statutory_note.txt",
        content=TAX_STATUTORY_TEXT,
        document_kind="tax_statutory_note",
        workstream_domain="tax",
    )
    _upload_text_document(
        client,
        case_id,
        title="Commercial revenue concentration note",
        filename="commercial_note.txt",
        content=COMMERCIAL_TEXT,
        document_kind="commercial_kpi_pack",
        workstream_domain="commercial",
        evidence_kind="risk",
    )
    _upload_text_document(
        client,
        case_id,
        title="Operations resilience note",
        filename="operations_note.txt",
        content=OPERATIONS_TEXT,
        document_kind="operations_review_pack",
        workstream_domain="operations",
        evidence_kind="risk",
    )
    _upload_text_document(
        client,
        case_id,
        title="Cyber privacy assessment",
        filename="cyber_note.txt",
        content=CYBER_TEXT,
        document_kind="cyber_privacy_pack",
        workstream_domain="cyber_privacy",
        evidence_kind="risk",
    )
    _upload_text_document(
        client,
        case_id,
        title="Forensic integrity review",
        filename="forensic_note.txt",
        content=FORENSIC_TEXT,
        document_kind="forensic_review_pack",
        workstream_domain="forensic_compliance",
        evidence_kind="risk",
    )
    request_response = client.post(
        f"/api/v1/cases/{case_id}/requests",
        json={
            "title": "Upload Day 1 owner map",
            "detail": "Need named owners for Day 1 and Day 100 integration dependencies.",
            "owner": "PMI Lead",
            "status": "open",
        },
    )
    assert request_response.status_code == 201

    response = client.get(f"/api/v1/cases/{case_id}/buy-side-analysis")
    assert response.status_code == 200
    analysis = response.json()

    assert len(analysis["valuation_bridge"]) >= 4
    assert len(analysis["spa_issues"]) >= 3
    assert len(analysis["pmi_risks"]) >= 3
    assert any("valuation bridge" in flag.lower() for flag in analysis["flags"])
    assert {update["template_key"] for update in analysis["checklist_updates"]} == {
        "financial_qoe.valuation_bridge",
        "legal_corporate.spa_issue_matrix",
        "operations.pmi_readiness_plan",
        "commercial.revenue_quality_story",
    }

    checklist_response = client.get(f"/api/v1/cases/{case_id}/checklist")
    assert checklist_response.status_code == 200
    statuses = {
        item["template_key"]: item["status"]
        for item in checklist_response.json()
        if item["template_key"]
    }
    assert statuses["financial_qoe.valuation_bridge"] == "satisfied"
    assert statuses["legal_corporate.spa_issue_matrix"] == "satisfied"
    assert statuses["operations.pmi_readiness_plan"] == "satisfied"
    assert statuses["commercial.revenue_quality_story"] == "satisfied"


def test_borrower_scorecard_endpoint_returns_structured_scores_and_updates_checklist(
    client,
) -> None:
    case_id = _create_case(client, motion_pack="credit_lending")
    _upload_financial_workbook(
        client,
        case_id,
        title="Borrower financial workbook",
        filename="borrower_financial_pack.xlsx",
        document_kind="borrower_financial_pack",
        bridge_variant="credit",
    )
    _upload_text_document(
        client,
        case_id,
        title="MCA secretarial summary",
        filename="mca_secretarial_summary.txt",
        content=MCA_SECRETARIAL_TEXT,
        document_kind="mca_secretarial_summary",
        workstream_domain="legal_corporate",
    )
    _upload_text_document(
        client,
        case_id,
        title="Lender monitoring note",
        filename="lender_monitoring_note.txt",
        content=COVENANT_MONITORING_TEXT,
        document_kind="lender_monitoring_note",
        workstream_domain="financial_qoe",
        evidence_kind="risk",
    )

    response = client.get(f"/api/v1/cases/{case_id}/borrower-scorecard")
    assert response.status_code == 200
    scorecard = response.json()

    assert scorecard["overall_score"] > 0
    assert scorecard["overall_rating"] in {"strong", "adequate", "watchlist", "stressed"}
    assert scorecard["financial_health"]["score"] > 0
    assert scorecard["collateral"]["score"] > 0
    assert scorecard["covenants"]["score"] > 0
    assert len(scorecard["covenant_tracking"]) >= 1
    assert {update["template_key"] for update in scorecard["checklist_updates"]} == {
        "financial_qoe.borrower_scorecard",
        "legal_corporate.collateral_cover_matrix",
        "regulatory.covenant_tracking_pack",
    }

    checklist_response = client.get(f"/api/v1/cases/{case_id}/checklist")
    assert checklist_response.status_code == 200
    statuses = {
        item["template_key"]: item["status"]
        for item in checklist_response.json()
        if item["template_key"]
    }
    assert statuses["financial_qoe.borrower_scorecard"] == "satisfied"
    assert statuses["legal_corporate.collateral_cover_matrix"] == "satisfied"
    assert statuses["regulatory.covenant_tracking_pack"] == "satisfied"


def test_vendor_risk_tier_endpoint_returns_structured_tier_and_updates_checklist(client) -> None:
    case_id = _create_case(client, motion_pack="vendor_onboarding")
    _upload_financial_workbook(
        client,
        case_id,
        title="Vendor financial workbook",
        filename="vendor_financial_pack.xlsx",
        document_kind="audited_financials",
    )
    _upload_text_document(
        client,
        case_id,
        title="Vendor regulatory note",
        filename="vendor_regulatory_note.txt",
        content=VENDOR_REGULATORY_TEXT,
        document_kind="vendor_regulatory_note",
        workstream_domain="regulatory",
        evidence_kind="fact",
    )
    _upload_text_document(
        client,
        case_id,
        title="Commercial revenue concentration note",
        filename="commercial_note.txt",
        content=COMMERCIAL_TEXT,
        document_kind="commercial_kpi_pack",
        workstream_domain="commercial",
        evidence_kind="risk",
    )
    _upload_text_document(
        client,
        case_id,
        title="Operations resilience note",
        filename="operations_note.txt",
        content=OPERATIONS_TEXT,
        document_kind="operations_review_pack",
        workstream_domain="operations",
        evidence_kind="risk",
    )
    _upload_text_document(
        client,
        case_id,
        title="Cyber privacy assessment",
        filename="cyber_note.txt",
        content=CYBER_TEXT,
        document_kind="cyber_privacy_pack",
        workstream_domain="cyber_privacy",
        evidence_kind="risk",
    )
    _upload_text_document(
        client,
        case_id,
        title="Forensic integrity review",
        filename="forensic_note.txt",
        content=FORENSIC_TEXT,
        document_kind="forensic_review_pack",
        workstream_domain="forensic_compliance",
        evidence_kind="risk",
    )

    response = client.get(f"/api/v1/cases/{case_id}/vendor-risk-tier")
    assert response.status_code == 200
    tier = response.json()

    factors = {item["factor"] for item in tier["scoring_breakdown"]}
    assert factors == {
        "service_criticality",
        "regulatory_screening",
        "cyber_privacy_posture",
        "integrity_risk",
        "operational_resilience",
        "financial_resilience",
    }
    assert tier["overall_score"] > 0
    assert tier["tier"] in {
        "tier_1_critical",
        "tier_2_high",
        "tier_3_moderate",
        "tier_4_low",
    }
    assert len(tier["questionnaire"]) == 5
    assert {update["template_key"] for update in tier["checklist_updates"]} == {
        "regulatory.vendor_risk_tier",
        "cyber_privacy.vendor_questionnaire",
        "cyber_privacy.vendor_certifications",
        "commercial.vendor_criticality_assessment",
    }
    assert "ISO 27001" not in tier["certifications_required"]

    checklist_response = client.get(f"/api/v1/cases/{case_id}/checklist")
    assert checklist_response.status_code == 200
    statuses = {
        item["template_key"]: item["status"]
        for item in checklist_response.json()
        if item["template_key"]
    }
    assert statuses["regulatory.vendor_risk_tier"] == "satisfied"
    assert statuses["cyber_privacy.vendor_questionnaire"] == "satisfied"
    assert statuses["cyber_privacy.vendor_certifications"] == "satisfied"
    assert statuses["commercial.vendor_criticality_assessment"] == "satisfied"


def test_phase11_motion_pack_specialist_attaches_when_structured_state_exists() -> None:
    from crewai_enterprise_pipeline_api.agents.crew import (
        CaseContext,
        WorkstreamContext,
        build_due_diligence_crew,
    )

    buy_side_analysis = BuySideAnalysis(
        case_id="case-1",
        valuation_bridge=[
            ValuationBridgeItem(
                label="QoE bridge",
                category="normalized_ebitda",
                amount=24.8,
                impact="Normalized EBITDA bridge is ready for IC discussion.",
            )
        ],
        spa_issues=[
            SpaIssueItem(
                title="Change-of-control consent risk",
                severity=FlagSeverity.HIGH,
                rationale="The customer MSA requires consent on change of control.",
                recommendation="Track consent as a CP in SPA drafting.",
            )
        ],
        pmi_risks=[
            PmiRiskItem(
                area="Operations",
                severity=FlagSeverity.MEDIUM,
                description="Single-site delivery creates continuity dependency.",
                day_one_action="Assign continuity owner for Day 1 planning.",
            )
        ],
        flags=["Valuation bridge ready for IC review."],
    )

    ctx = CaseContext(
        case_id="case-1",
        case_name="Phase 11 Crew",
        target_name="Crew Motion Pack",
        country="India",
        motion_pack="buy_side_diligence",
        sector_pack="tech_saas_services",
        document_count=4,
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

    crew, _, tool_map = build_due_diligence_crew(
        ctx,
        settings,
        buy_side_analysis=buy_side_analysis,
    )

    assert len(crew.agents) == 4
    assert "motion_pack_specialist" in tool_map
    assert "review_buy_side_pack" in {tool.name for tool in tool_map["motion_pack_specialist"]}
    assert "review_buy_side_pack" in {tool.name for tool in tool_map["coordinator"]}
    assert "motion_pack_analysis" in {task.name for task in crew.tasks}


def test_workflow_run_persists_phase11_refresh_and_motion_pack_highlights(client) -> None:
    case_id = _create_case(client, motion_pack="buy_side_diligence")
    _upload_financial_workbook(
        client,
        case_id,
        title="Audited financial workbook",
        filename="audited_financials.xlsx",
        document_kind="audited_financials",
        bridge_variant="workflow",
    )
    _upload_text_document(
        client,
        case_id,
        title="MCA secretarial summary",
        filename="mca_secretarial_summary.txt",
        content=MCA_SECRETARIAL_TEXT,
        document_kind="mca_secretarial_summary",
        workstream_domain="legal_corporate",
    )
    _upload_text_document(
        client,
        case_id,
        title="Enterprise customer MSA",
        filename="enterprise_customer_msa.txt",
        content=CUSTOMER_MSA_TEXT,
        document_kind="customer_msa",
        workstream_domain="legal_corporate",
        evidence_kind="contract",
    )
    _upload_text_document(
        client,
        case_id,
        title="Tax statutory note",
        filename="tax_statutory_note.txt",
        content=TAX_STATUTORY_TEXT,
        document_kind="tax_statutory_note",
        workstream_domain="tax",
    )
    _upload_text_document(
        client,
        case_id,
        title="Commercial revenue concentration note",
        filename="commercial_note.txt",
        content=COMMERCIAL_TEXT,
        document_kind="commercial_kpi_pack",
        workstream_domain="commercial",
        evidence_kind="risk",
    )
    _upload_text_document(
        client,
        case_id,
        title="Operations resilience note",
        filename="operations_note.txt",
        content=OPERATIONS_TEXT,
        document_kind="operations_review_pack",
        workstream_domain="operations",
        evidence_kind="risk",
    )
    _upload_text_document(
        client,
        case_id,
        title="Cyber privacy assessment",
        filename="cyber_note.txt",
        content=CYBER_TEXT,
        document_kind="cyber_privacy_pack",
        workstream_domain="cyber_privacy",
        evidence_kind="risk",
    )
    _upload_text_document(
        client,
        case_id,
        title="Forensic integrity review",
        filename="forensic_note.txt",
        content=FORENSIC_TEXT,
        document_kind="forensic_review_pack",
        workstream_domain="forensic_compliance",
        evidence_kind="risk",
    )
    client.post(
        f"/api/v1/cases/{case_id}/requests",
        json={
            "title": "Upload Day 1 owner map",
            "detail": "Need named owners for Day 1 and Day 100 integration dependencies.",
            "owner": "PMI Lead",
            "status": "open",
        },
    )

    run_response = client.post(
        f"/api/v1/cases/{case_id}/runs",
        json={"requested_by": "phase11-runner"},
    )
    assert run_response.status_code == 201
    payload = run_response.json()

    trace_steps = {event["step_key"] for event in payload["run"]["trace_events"]}
    assert "motion_pack_deepening_refresh" in trace_steps

    syntheses = {
        synthesis["workstream_domain"]: synthesis
        for synthesis in payload["run"]["workstream_syntheses"]
    }
    assert "Phase 11 buy-side deepening" in syntheses["financial_qoe"]["narrative"]
    assert "Phase 11 buy-side deepening" in syntheses["legal_corporate"]["narrative"]
    assert "Phase 11 buy-side deepening" in syntheses["operations"]["narrative"]

    assert payload["executive_memo"]["motion_pack_highlights"]
    assert "Phase 11 buy-side deepening identified" in payload["executive_memo"][
        "executive_summary"
    ]
