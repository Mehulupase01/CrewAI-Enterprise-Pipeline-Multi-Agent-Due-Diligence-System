from __future__ import annotations

from unittest.mock import MagicMock

from crewai_enterprise_pipeline_api.domain.models import (
    CommercialConcentrationSignal,
    CommercialRenewalSignal,
    CommercialSummary,
    ComplianceStatus,
    CyberControlCheck,
    CyberPrivacySummary,
    FlagSeverity,
    ForensicFlag,
    ForensicFlagType,
    ForensicSummary,
    OperationsDependencySignal,
    OperationsSummary,
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


def _create_case(
    client,
    *,
    motion_pack: str = "vendor_onboarding",
    sector_pack: str = "tech_saas_services",
) -> str:
    response = client.post(
        "/api/v1/cases",
        json={
            "name": f"Project Phase10 {motion_pack}",
            "target_name": "Phase10 Signals Private Limited",
            "summary": "Phase 10 commercial, operations, cyber, and forensic validation case.",
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


def test_phase10_endpoints_return_structured_summaries_and_flags(client) -> None:
    case_id = _create_case(client)
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

    commercial_response = client.get(f"/api/v1/cases/{case_id}/commercial-summary")
    assert commercial_response.status_code == 200
    commercial_summary = commercial_response.json()
    assert commercial_summary["concentration_signals"][0]["share_of_revenue"] == 0.7
    assert commercial_summary["net_revenue_retention"] == 1.18
    assert commercial_summary["churn_rate"] == 0.04
    assert any(
        signal["status"] == "due_soon" for signal in commercial_summary["renewal_signals"]
    )
    assert any("pricing pressure" in flag.lower() for flag in commercial_summary["flags"])
    assert {update["template_key"] for update in commercial_summary["checklist_updates"]} == {
        "commercial.customer_concentration"
    }

    operations_response = client.get(f"/api/v1/cases/{case_id}/operations-summary")
    assert operations_response.status_code == 200
    operations_summary = operations_response.json()
    assert operations_summary["supplier_concentration_top_3"] == 0.65
    assert operations_summary["single_site_dependency"] is True
    assert len(operations_summary["key_person_dependencies"]) >= 1
    updated_keys = {update["template_key"] for update in operations_summary["checklist_updates"]}
    assert {"operations.service_continuity", "operations.delivery_model"}.issubset(updated_keys)

    cyber_response = client.get(f"/api/v1/cases/{case_id}/cyber-summary")
    assert cyber_response.status_code == 200
    cyber_summary = cyber_response.json()
    control_statuses = {item["control_key"]: item["status"] for item in cyber_summary["controls"]}
    assert control_statuses["consent_mechanism"] == "compliant"
    assert control_statuses["retention_policy"] == "compliant"
    assert control_statuses["significant_data_fiduciary_registration"] == "partially_compliant"
    assert control_statuses["iso_27001"] == "compliant"
    assert control_statuses["soc2"] == "non_compliant"
    assert "ISO 27001" in cyber_summary["certifications"]
    assert "SOC 2" not in cyber_summary["certifications"]
    assert len(cyber_summary["breach_history"]) == 1
    assert any("SOC 2 appears non-compliant" in flag for flag in cyber_summary["flags"])
    assert any("partially compliant" in flag for flag in cyber_summary["flags"])
    cyber_updated_keys = {update["template_key"] for update in cyber_summary["checklist_updates"]}
    assert {"cyber.privacy_controls", "cyber_privacy.vendor_security_posture"}.issubset(
        cyber_updated_keys
    )

    forensic_response = client.get(f"/api/v1/cases/{case_id}/forensic-flags")
    assert forensic_response.status_code == 200
    forensic_flags = forensic_response.json()
    assert {flag["flag_type"] for flag in forensic_flags} == {
        "RELATED_PARTY",
        "ROUND_TRIPPING",
        "REVENUE_ANOMALY",
        "LITIGATION",
    }

    checklist_response = client.get(f"/api/v1/cases/{case_id}/checklist")
    assert checklist_response.status_code == 200
    checklist_statuses = {
        item["template_key"]: item["status"]
        for item in checklist_response.json()
        if item["template_key"]
    }
    assert checklist_statuses["commercial.customer_concentration"] == "satisfied"
    assert checklist_statuses["operations.service_continuity"] == "satisfied"
    assert checklist_statuses["operations.delivery_model"] == "satisfied"
    assert checklist_statuses["cyber.privacy_controls"] == "satisfied"
    assert checklist_statuses["cyber_privacy.vendor_security_posture"] == "satisfied"
    assert checklist_statuses["forensic.third_party_integrity"] == "satisfied"
    assert checklist_statuses["regulatory.vendor_restrictions"] == "pending"


def test_phase10_tools_attach_for_relevant_workstreams() -> None:
    from crewai_enterprise_pipeline_api.agents.crew import (
        CaseContext,
        WorkstreamContext,
        build_due_diligence_crew,
    )

    commercial_summary = CommercialSummary(
        case_id="case-1",
        concentration_signals=[
            CommercialConcentrationSignal(
                subject="Top customer",
                share_of_revenue=0.7,
                note="Top customer contributes 70% of ARR.",
            )
        ],
        net_revenue_retention=1.18,
        churn_rate=0.04,
        pricing_signals=[
            "Pricing pressure increased after a discount requested by the top customer."
        ],
        renewal_signals=[
            CommercialRenewalSignal(
                counterparty="Top customer",
                status="due_soon",
                note="Renewal due next quarter.",
            )
        ],
        flags=["Customer concentration is elevated: Top customer accounts for 70% of revenue."],
    )
    operations_summary = OperationsSummary(
        case_id="case-1",
        supplier_concentration_top_3=0.65,
        dependency_signals=[
            OperationsDependencySignal(
                dependency_type="site",
                label="Single-site or continuity dependency",
                detail="A single plant handles all capacity.",
            )
        ],
        single_site_dependency=True,
        key_person_dependencies=["The business is founder dependent."],
        flags=[
            "Single-site or continuity dependency signals were detected in operational materials."
        ],
    )
    cyber_summary = CyberPrivacySummary(
        case_id="case-1",
        controls=[
            CyberControlCheck(
                control_key="consent_mechanism",
                status=ComplianceStatus.COMPLIANT,
                notes="Consent mechanism implemented.",
            )
        ],
        certifications=["ISO 27001"],
        breach_history=[
            "A security incident involving unauthorized access was reported last year."
        ],
        flags=[
            "significant_data_fiduciary_registration appears partially compliant or "
            "under remediation."
        ],
    )
    forensic_summary = ForensicSummary(
        case_id="case-1",
        flags=[
            ForensicFlag(
                flag_type=ForensicFlagType.RELATED_PARTY,
                severity=FlagSeverity.HIGH,
                description="Related-party patterns require governance review.",
            )
        ],
    )

    ctx = CaseContext(
        case_id="case-1",
        case_name="Phase 10 Crew",
        target_name="Crew Phase 10",
        country="India",
        motion_pack="vendor_onboarding",
        sector_pack="tech_saas_services",
        document_count=4,
        workstreams={
            "commercial": WorkstreamContext(domain="commercial"),
            "operations": WorkstreamContext(domain="operations"),
            "cyber_privacy": WorkstreamContext(domain="cyber_privacy"),
            "forensic_compliance": WorkstreamContext(domain="forensic_compliance"),
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

    _, _, tool_map = build_due_diligence_crew(
        ctx,
        settings,
        commercial_summary=commercial_summary,
        operations_summary=operations_summary,
        cyber_summary=cyber_summary,
        forensic_summary=forensic_summary,
    )

    assert "review_commercial_signals" in {
        tool.name for tool in tool_map["commercial"]
    }
    assert "review_operations_risks" in {
        tool.name for tool in tool_map["operations"]
    }
    assert "review_cyber_controls" in {
        tool.name for tool in tool_map["cyber_privacy"]
    }
    assert "review_forensic_flags" in {
        tool.name for tool in tool_map["forensic_compliance"]
    }

    coordinator_tools = {tool.name for tool in tool_map["coordinator"]}
    assert {
        "review_commercial_signals",
        "review_operations_risks",
        "review_cyber_controls",
        "review_forensic_flags",
    }.issubset(coordinator_tools)


def test_workflow_run_persists_phase10_refresh_and_enriched_syntheses(client) -> None:
    case_id = _create_case(client)
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

    run_response = client.post(
        f"/api/v1/cases/{case_id}/runs",
        json={"requested_by": "phase10-runner"},
    )
    assert run_response.status_code == 201
    payload = run_response.json()

    trace_steps = {event["step_key"] for event in payload["run"]["trace_events"]}
    assert "commercial_operations_cyber_forensic_refresh" in trace_steps

    syntheses = {
        synthesis["workstream_domain"]: synthesis
        for synthesis in payload["run"]["workstream_syntheses"]
    }
    assert "Structured commercial analysis identified" in syntheses["commercial"]["narrative"]
    assert "Structured operations analysis identified" in syntheses["operations"]["narrative"]
    assert (
        "Structured cyber/privacy analysis identified"
        in syntheses["cyber_privacy"]["narrative"]
    )
    assert (
        "Structured forensic analysis identified"
        in syntheses["forensic_compliance"]["narrative"]
    )
    assert "Phase 10 engines identified" in payload["executive_memo"]["executive_summary"]
