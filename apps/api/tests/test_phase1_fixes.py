"""Phase 1 tests: critical fixes and dependency repair."""

from unittest.mock import patch

import pytest


def test_approval_decision_override(client) -> None:
    """POST review with decision=REJECTED -> stored decision is REJECTED."""
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Override",
            "target_name": "Override Systems Private Limited",
            "summary": "Approval decision override test case.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case_response.json()["id"]

    client.post(f"/api/v1/cases/{case_id}/checklist/seed")

    # Without override the auto-computed decision would be changes_requested
    # (checklist items are open). Override it to rejected.
    approval_response = client.post(
        f"/api/v1/cases/{case_id}/approvals/review",
        json={
            "reviewer": "IC Reviewer",
            "note": "Rejected by reviewer override.",
            "decision": "rejected",
        },
    )
    assert approval_response.status_code == 201
    assert approval_response.json()["decision"] == "rejected"

    # Also test conditionally_approved override
    approval_response2 = client.post(
        f"/api/v1/cases/{case_id}/approvals/review",
        json={
            "reviewer": "IC Reviewer",
            "note": "Conditionally approved by reviewer override.",
            "decision": "conditionally_approved",
        },
    )
    assert approval_response2.status_code == 201
    assert approval_response2.json()["decision"] == "conditionally_approved"


def test_issue_scan_word_boundary(client) -> None:
    """Evidence with 'cash flow' should not match 'cash' alone if only multi-word patterns exist.

    More specifically, the word 'charge' pattern should match 'charge' as a
    standalone word but NOT when it appears inside another word.
    """
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Boundary",
            "target_name": "Boundary Analytics Private Limited",
            "summary": "Word boundary regex test case.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case_response.json()["id"]

    # "surcharge" contains "charge" but should NOT trigger the encumbrance rule
    # because we now use word-boundary matching.
    evidence_no_match = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={
            "title": "Payment surcharge summary",
            "evidence_kind": "fact",
            "workstream_domain": "financial_qoe",
            "citation": "Invoice analysis FY26",
            "excerpt": "The company applied a surcharge on late payments collected in Q4.",
            "confidence": 0.8,
        },
    )
    assert evidence_no_match.status_code == 201

    scan_response = client.post(f"/api/v1/cases/{case_id}/issues/scan")
    assert scan_response.status_code == 201
    assert scan_response.json()["created_count"] == 0

    # "charge" as a standalone word SHOULD trigger the encumbrance rule.
    evidence_match = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={
            "title": "Charge register extract",
            "evidence_kind": "risk",
            "workstream_domain": "legal_corporate",
            "citation": "MCA charge register FY26",
            "excerpt": "An open charge was found that has not been satisfied.",
            "confidence": 0.9,
        },
    )
    assert evidence_match.status_code == 201

    scan_response2 = client.post(f"/api/v1/cases/{case_id}/issues/scan")
    assert scan_response2.status_code == 201
    assert scan_response2.json()["created_count"] >= 1


def test_parser_corrupt_file(client) -> None:
    """Upload corrupt PDF -> 201 response with empty text, no crash."""
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Corrupt",
            "target_name": "Corrupt Files Private Limited",
            "summary": "Corrupt file parser test case.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case_response.json()["id"]

    # Upload a corrupt PDF (random bytes, not a valid PDF)
    upload_response = client.post(
        f"/api/v1/cases/{case_id}/documents/upload",
        data={
            "document_kind": "audited_financials",
            "source_kind": "uploaded_dataroom",
            "workstream_domain": "financial_qoe",
            "title": "Corrupt PDF",
            "evidence_kind": "fact",
        },
        files={
            "file": (
                "corrupt.pdf",
                b"\x00\x01\x02\x03\x04\x05NOTAPDF",
                "application/pdf",
            )
        },
    )
    assert upload_response.status_code == 201
    payload = upload_response.json()
    assert payload["parser_name"] == "pdfplumber"
    # Should still succeed, just with empty/minimal text
    assert payload["extracted_character_count"] == 0


def test_workflow_run_failure(client) -> None:
    """Execute run with mocked failure -> status becomes FAILED, trace event logged."""
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Failure",
            "target_name": "Failure Analytics Private Limited",
            "summary": "Workflow failure handling test case.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case_response.json()["id"]

    client.post(f"/api/v1/cases/{case_id}/checklist/seed")

    # Patch the report service to raise an error during the run.
    # TestClient raises server exceptions by default, so we catch them.
    with patch(
        "crewai_enterprise_pipeline_api.services.workflow_service.ReportService"
    ) as mock_report:
        mock_report.return_value.build_executive_memo.side_effect = RuntimeError(
            "Simulated failure"
        )
        with pytest.raises(RuntimeError, match="Simulated failure"):
            client.post(
                f"/api/v1/cases/{case_id}/runs",
                json={
                    "requested_by": "Test Operator",
                    "note": "This run should fail.",
                },
            )

    # Verify the run was marked FAILED
    runs_response = client.get(f"/api/v1/cases/{case_id}/runs")
    assert runs_response.status_code == 200
    runs = runs_response.json()
    assert len(runs) == 1
    assert runs[0]["status"] == "failed"
    assert "Simulated failure" in runs[0]["summary"]

    # Verify a failure trace event was logged
    run_id = runs[0]["id"]
    detail_response = client.get(f"/api/v1/cases/{case_id}/runs/{run_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    failure_events = [
        e for e in detail["trace_events"] if e["step_key"] == "run_failure"
    ]
    assert len(failure_events) == 1
    assert "Simulated failure" in failure_events[0]["message"]


def test_health_overview_uses_config_settings(client) -> None:
    """Overview endpoint uses configurable product_name, current_phase, country."""
    response = client.get("/api/v1/system/overview")
    assert response.status_code == 200
    payload = response.json()
    # These should now come from Settings, not be hardcoded
    assert payload["product_name"] == "CrewAI Enterprise Pipeline"
    assert "Phase" in payload["current_phase"]
    assert payload["country"] == "India"
