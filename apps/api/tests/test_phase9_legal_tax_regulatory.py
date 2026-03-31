from __future__ import annotations

from unittest.mock import MagicMock

from crewai_enterprise_pipeline_api.domain.models import (
    ComplianceMatrixItem,
    ComplianceMatrixSummary,
    ComplianceStatus,
    ContractClauseReview,
    ContractReviewResult,
    LegalStructureSummary,
    SectorPack,
    TaxComplianceItem,
    TaxComplianceSummary,
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

RBI_REGULATORY_TEXT = (
    "RBI certificate of registration remains current and valid. "
    "NBFC registration is compliant. Prudential returns filed and CRAR remains "
    "within threshold. SEBI disclosure calendar current and compliant."
)


def _create_case(client, *, motion_pack: str = "buy_side_diligence", sector_pack: str) -> str:
    response = client.post(
        "/api/v1/cases",
        json={
            "name": f"Project Phase9 {sector_pack}",
            "target_name": "Meridian Finance Private Limited",
            "summary": "Phase 9 legal, tax, and regulatory validation case.",
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


def test_legal_summary_endpoint_extracts_directors_contract_clauses_and_flags(client) -> None:
    case_id = _create_case(client, sector_pack="tech_saas_services")
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

    summary_response = client.get(f"/api/v1/cases/{case_id}/legal-summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()

    assert len(summary["directors"]) >= 2
    assert summary["shareholding_summary"]["promoter"] == 62.5
    assert "Meridian Payments Private Limited" in summary["subsidiary_mentions"]
    assert summary["charges_detected"] >= 1
    assert len(summary["contract_reviews"]) >= 1

    clause_keys = {
        clause["clause_key"]
        for review in summary["contract_reviews"]
        for clause in review["clauses"]
        if clause["present"]
    }
    assert {
        "change_of_control",
        "assignment",
        "termination",
        "indemnity",
        "liability_cap",
        "governing_law",
    }.issubset(clause_keys)
    assert any("change-of-control clause detected" in flag.lower() for flag in summary["flags"])
    assert any("charge or encumbrance" in flag.lower() for flag in summary["flags"])

    updated_keys = {update["template_key"] for update in summary["checklist_updates"]}
    assert updated_keys == {
        "legal_corporate.cap_table",
        "legal_corporate.material_contracts",
    }


def test_tax_summary_endpoint_extracts_gstin_statuses_and_checklist_updates(client) -> None:
    case_id = _create_case(client, sector_pack="tech_saas_services")
    _upload_text_document(
        client,
        case_id,
        title="Tax statutory note",
        filename="tax_statutory_note.txt",
        content=TAX_STATUTORY_TEXT,
        document_kind="tax_statutory_note",
        workstream_domain="tax",
    )

    summary_response = client.get(f"/api/v1/cases/{case_id}/tax-summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()

    assert summary["gstins"] == ["27ABCDE1234F1Z5"]
    status_map = {item["tax_area"]: item["status"] for item in summary["items"]}
    assert status_map == {
        "gst": "compliant",
        "income_tax": "compliant",
        "tds_payroll": "compliant",
        "transfer_pricing": "compliant",
        "deferred_tax": "compliant",
    }
    assert any("transfer-pricing evidence detected" in flag.lower() for flag in summary["flags"])
    assert any("deferred-tax or mat-credit references" in flag.lower() for flag in summary["flags"])
    assert {update["template_key"] for update in summary["checklist_updates"]} == {
        "tax.notice_register"
    }


def test_compliance_matrix_endpoint_returns_bfsi_regulation_statuses(client) -> None:
    case_id = _create_case(client, sector_pack="bfsi_nbfc")
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
        title="RBI regulatory note",
        filename="rbi_regulatory_note.txt",
        content=RBI_REGULATORY_TEXT,
        document_kind="rbi_regulatory_note",
        workstream_domain="regulatory",
    )

    response = client.get(f"/api/v1/cases/{case_id}/compliance-matrix")
    assert response.status_code == 200
    matrix = response.json()
    status_map = {item["regulation"]: item["status"] for item in matrix}

    assert status_map["MCA Statutory Filings"] == "compliant"
    assert status_map["RBI NBFC Registration"] == "compliant"
    assert status_map["RBI / Prudential Returns"] == "compliant"
    assert status_map["SEBI / Capital Markets Compliance"] == "compliant"

    checklist_response = client.get(f"/api/v1/cases/{case_id}/checklist")
    assert checklist_response.status_code == 200
    checklist_statuses = {
        item["template_key"]: item["status"]
        for item in checklist_response.json()
        if item["template_key"]
    }
    assert checklist_statuses["regulatory.mca_consistency"] == "satisfied"
    assert checklist_statuses["regulatory.rbi_registration_and_returns"] == "satisfied"


def test_phase9_compliance_tools_attach_for_relevant_workstreams() -> None:
    from crewai_enterprise_pipeline_api.agents.crew import (
        CaseContext,
        WorkstreamContext,
        build_due_diligence_crew,
    )

    legal_summary = LegalStructureSummary(
        case_id="case-1",
        artifact_count=2,
        contract_reviews=[
            ContractReviewResult(
                artifact_id="doc-1",
                contract_title="Enterprise customer MSA",
                contract_type="customer_agreement",
                governing_law="India",
                clauses=[
                    ContractClauseReview(
                        clause_key="change_of_control",
                        present=True,
                        note="Change-of-control termination clause detected.",
                    )
                ],
                flags=[],
            )
        ],
        flags=[],
    )
    tax_summary = TaxComplianceSummary(
        case_id="case-1",
        gstins=["27ABCDE1234F1Z5"],
        items=[
            TaxComplianceItem(
                tax_area="gst",
                status=ComplianceStatus.COMPLIANT,
                notes="GST returns filed on time.",
            )
        ],
        flags=[],
    )
    compliance_summary = ComplianceMatrixSummary(
        case_id="case-1",
        sector_pack=SectorPack.BFSI_NBFC,
        items=[
            ComplianceMatrixItem(
                regulation="RBI NBFC Registration",
                regulator="Reserve Bank of India",
                status=ComplianceStatus.COMPLIANT,
                notes="Certificate of registration remains valid.",
            )
        ],
        flags=[],
    )

    ctx = CaseContext(
        case_id="case-1",
        case_name="Phase 9 Crew",
        target_name="Crew Compliance",
        country="India",
        motion_pack="buy_side_diligence",
        sector_pack="bfsi_nbfc",
        document_count=4,
        workstreams={
            "legal_corporate": WorkstreamContext(domain="legal_corporate"),
            "tax": WorkstreamContext(domain="tax"),
            "regulatory": WorkstreamContext(domain="regulatory"),
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
        legal_summary=legal_summary,
        tax_summary=tax_summary,
        compliance_summary=compliance_summary,
    )

    legal_tool_names = {tool.name for tool in tool_map["legal_corporate"]}
    tax_tool_names = {tool.name for tool in tool_map["tax"]}
    regulatory_tool_names = {tool.name for tool in tool_map["regulatory"]}
    coordinator_tool_names = {tool.name for tool in tool_map["coordinator"]}

    assert "review_contract_clauses" in legal_tool_names
    assert "review_tax_compliance" in tax_tool_names
    assert "review_compliance_matrix" in regulatory_tool_names
    assert "review_contract_clauses" in coordinator_tool_names
    assert "review_tax_compliance" in coordinator_tool_names
    assert "review_compliance_matrix" in coordinator_tool_names


def test_workflow_run_persists_phase9_refresh_and_enriched_syntheses(client) -> None:
    case_id = _create_case(client, sector_pack="bfsi_nbfc")
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
        title="RBI regulatory note",
        filename="rbi_regulatory_note.txt",
        content=RBI_REGULATORY_TEXT,
        document_kind="rbi_regulatory_note",
        workstream_domain="regulatory",
    )

    run_response = client.post(
        f"/api/v1/cases/{case_id}/runs",
        json={"requested_by": "phase9-runner"},
    )
    assert run_response.status_code == 201
    payload = run_response.json()

    trace_steps = {event["step_key"] for event in payload["run"]["trace_events"]}
    assert "legal_tax_regulatory_refresh" in trace_steps

    syntheses = {
        synthesis["workstream_domain"]: synthesis
        for synthesis in payload["run"]["workstream_syntheses"]
    }
    assert "Structured legal analysis identified" in syntheses["legal_corporate"]["narrative"]
    assert "Structured tax analysis identified" in syntheses["tax"]["narrative"]
    assert "Compliance matrix generated" in syntheses["regulatory"]["narrative"]
    assert "Phase 9 engines identified" in payload["executive_memo"]["executive_summary"]
