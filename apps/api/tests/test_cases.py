def test_case_workflow_persists_documents_evidence_and_trackers(client) -> None:
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Alpha Nimbus Acquisition",
            "target_name": "Nimbus Data Systems",
            "summary": "India buy-side diligence for a vertical SaaS target.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    assert case_response.status_code == 201
    case_payload = case_response.json()
    case_id = case_payload["id"]

    list_response = client.get("/api/v1/cases")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    document_response = client.post(
        f"/api/v1/cases/{case_id}/documents",
        json={
            "title": "FY25 audited financials",
            "source_kind": "uploaded_dataroom",
            "document_kind": "audited_financials",
            "mime_type": "application/pdf",
            "processing_status": "received",
            "storage_path": "minio://cases/alpha/fy25-audited-financials.pdf",
        },
    )
    assert document_response.status_code == 201
    document_payload = document_response.json()

    evidence_response = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={
            "title": "Deferred revenue reconciliation",
            "evidence_kind": "metric",
            "workstream_domain": "financial_qoe",
            "citation": "FY25 audited financials, Note 12",
            "excerpt": "Deferred revenue increased by 28 percent driven by annual contracts.",
            "artifact_id": document_payload["id"],
            "confidence": 0.91,
        },
    )
    assert evidence_response.status_code == 201

    request_response = client.post(
        f"/api/v1/cases/{case_id}/requests",
        json={
            "title": "Provide monthly churn bridge",
            "detail": (
                "Need a monthly logo churn and net revenue retention bridge "
                "for the last 24 months."
            ),
            "owner": "Finance Controller",
            "status": "open",
        },
    )
    assert request_response.status_code == 201

    qa_response = client.post(
        f"/api/v1/cases/{case_id}/qa",
        json={
            "question": "Why did implementation revenue spike in Q3 FY25?",
            "requested_by": "Financial workstream",
            "response": (
                "Two enterprise onboarding projects were recognized after "
                "acceptance milestones."
            ),
            "status": "answered",
        },
    )
    assert qa_response.status_code == 201

    detail_response = client.get(f"/api/v1/cases/{case_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["motion_pack"] == "buy_side_diligence"
    assert len(detail_payload["documents"]) == 1
    assert len(detail_payload["evidence_items"]) == 1
    assert len(detail_payload["request_items"]) == 1
    assert len(detail_payload["qa_items"]) == 1
    assert detail_payload["evidence_items"][0]["workstream_domain"] == "financial_qoe"


def test_case_detail_returns_404_for_unknown_case(client) -> None:
    response = client.get("/api/v1/cases/non-existent-case")
    assert response.status_code == 404
