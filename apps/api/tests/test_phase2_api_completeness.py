"""Phase 2 tests: API completeness -- PATCH, DELETE, individual GET, pagination, download."""


def _create_case(client, **overrides):
    defaults = {
        "name": "Phase 2 Test Case",
        "target_name": "Phase2 Corp Private Limited",
        "summary": "Phase 2 test.",
        "motion_pack": "buy_side_diligence",
        "sector_pack": "tech_saas_services",
        "country": "India",
    }
    defaults.update(overrides)
    resp = client.post("/api/v1/cases", json=defaults)
    assert resp.status_code == 201
    return resp.json()["id"]


def test_patch_case(client) -> None:
    """Create case -> PATCH name -> GET -> assert name updated."""
    case_id = _create_case(client, name="Original Name")

    patch_response = client.patch(
        f"/api/v1/cases/{case_id}",
        json={"name": "Updated Name", "status": "active"},
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["name"] == "Updated Name"
    assert patched["status"] == "active"

    get_response = client.get(f"/api/v1/cases/{case_id}")
    assert get_response.json()["name"] == "Updated Name"
    assert get_response.json()["status"] == "active"


def test_delete_case_cascade(client) -> None:
    """Create case + documents + issues -> DELETE case -> assert all children gone."""
    case_id = _create_case(client, name="To Be Deleted")

    # Add a document
    client.post(
        f"/api/v1/cases/{case_id}/documents",
        json={
            "title": "Test doc",
            "source_kind": "uploaded_dataroom",
            "document_kind": "audited_financials",
        },
    )

    # Add an issue
    client.post(
        f"/api/v1/cases/{case_id}/issues",
        json={
            "title": "Test issue",
            "summary": "A test issue for cascade delete.",
            "severity": "medium",
            "workstream_domain": "financial_qoe",
            "business_impact": "Test impact.",
            "confidence": 0.8,
        },
    )

    # Verify children exist
    assert len(client.get(f"/api/v1/cases/{case_id}/documents").json()) == 1
    assert len(client.get(f"/api/v1/cases/{case_id}/issues").json()) == 1

    # Delete the case
    delete_response = client.delete(f"/api/v1/cases/{case_id}")
    assert delete_response.status_code == 204

    # Case should be gone
    assert client.get(f"/api/v1/cases/{case_id}").status_code == 404


def test_get_single_document(client) -> None:
    """Upload doc -> GET by doc_id -> assert fields match."""
    case_id = _create_case(client, name="Doc Retrieval Test")

    upload_response = client.post(
        f"/api/v1/cases/{case_id}/documents/upload",
        data={
            "document_kind": "management_memo",
            "source_kind": "uploaded_dataroom",
            "workstream_domain": "financial_qoe",
            "title": "Test Memo",
            "evidence_kind": "fact",
        },
        files={"file": ("memo.txt", b"Revenue grew 32 percent.", "text/plain")},
    )
    assert upload_response.status_code == 201
    doc_id = upload_response.json()["artifact"]["id"]

    get_response = client.get(f"/api/v1/cases/{case_id}/documents/{doc_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == doc_id
    assert get_response.json()["title"] == "Test Memo"


def test_delete_document(client) -> None:
    """Create document -> DELETE -> verify 404 on GET."""
    case_id = _create_case(client, name="Doc Delete Test")

    doc_response = client.post(
        f"/api/v1/cases/{case_id}/documents",
        json={
            "title": "Deletable doc",
            "source_kind": "uploaded_dataroom",
            "document_kind": "audited_financials",
        },
    )
    doc_id = doc_response.json()["id"]

    delete_response = client.delete(f"/api/v1/cases/{case_id}/documents/{doc_id}")
    assert delete_response.status_code == 204

    assert client.get(f"/api/v1/cases/{case_id}/documents/{doc_id}").status_code == 404


def test_get_single_evidence_and_patch(client) -> None:
    """Create evidence -> GET by id -> PATCH confidence -> verify updated."""
    case_id = _create_case(client, name="Evidence CRUD Test")

    evidence_response = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={
            "title": "Revenue metric",
            "evidence_kind": "metric",
            "workstream_domain": "financial_qoe",
            "citation": "FY25 financials",
            "excerpt": "Revenue grew 28 percent year over year.",
            "confidence": 0.8,
        },
    )
    ev_id = evidence_response.json()["id"]

    # GET single
    get_response = client.get(f"/api/v1/cases/{case_id}/evidence/{ev_id}")
    assert get_response.status_code == 200
    assert get_response.json()["confidence"] == 0.8

    # PATCH
    patch_response = client.patch(
        f"/api/v1/cases/{case_id}/evidence/{ev_id}",
        json={"confidence": 0.95, "title": "Updated revenue metric"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["confidence"] == 0.95
    assert patch_response.json()["title"] == "Updated revenue metric"


def test_get_single_issue_and_patch(client) -> None:
    """Create issue -> GET by id -> PATCH status -> verify."""
    case_id = _create_case(client, name="Issue CRUD Test")

    issue_response = client.post(
        f"/api/v1/cases/{case_id}/issues",
        json={
            "title": "Test issue",
            "summary": "A patchable issue.",
            "severity": "high",
            "workstream_domain": "tax",
            "business_impact": "Test impact.",
            "confidence": 0.85,
        },
    )
    issue_id = issue_response.json()["id"]

    get_response = client.get(f"/api/v1/cases/{case_id}/issues/{issue_id}")
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "open"

    patch_response = client.patch(
        f"/api/v1/cases/{case_id}/issues/{issue_id}",
        json={"status": "closed", "severity": "low"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "closed"
    assert patch_response.json()["severity"] == "low"


def test_delete_issue(client) -> None:
    """Create issue -> DELETE -> verify 404."""
    case_id = _create_case(client, name="Issue Delete Test")

    issue_response = client.post(
        f"/api/v1/cases/{case_id}/issues",
        json={
            "title": "Deletable issue",
            "summary": "Will be deleted.",
            "severity": "medium",
            "workstream_domain": "legal_corporate",
            "business_impact": "None.",
            "confidence": 0.7,
        },
    )
    issue_id = issue_response.json()["id"]

    assert client.delete(f"/api/v1/cases/{case_id}/issues/{issue_id}").status_code == 204
    assert client.get(f"/api/v1/cases/{case_id}/issues/{issue_id}").status_code == 404


def test_patch_request_item(client) -> None:
    """Create request -> PATCH status and owner -> verify."""
    case_id = _create_case(client, name="Request PATCH Test")

    req_response = client.post(
        f"/api/v1/cases/{case_id}/requests",
        json={
            "title": "Upload financials",
            "detail": "Need audited financials for FY25.",
            "owner": "Finance Team",
            "status": "open",
        },
    )
    item_id = req_response.json()["id"]

    patch_response = client.patch(
        f"/api/v1/cases/{case_id}/requests/{item_id}",
        json={"status": "received", "owner": "Audit Manager"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "received"
    assert patch_response.json()["owner"] == "Audit Manager"


def test_patch_qa_item(client) -> None:
    """Create QA item -> PATCH response and status -> verify."""
    case_id = _create_case(client, name="QA PATCH Test")

    qa_response = client.post(
        f"/api/v1/cases/{case_id}/qa",
        json={
            "question": "Why did revenue spike?",
            "requested_by": "Financial analyst",
            "status": "open",
        },
    )
    item_id = qa_response.json()["id"]

    patch_response = client.patch(
        f"/api/v1/cases/{case_id}/qa/{item_id}",
        json={
            "response": "Two enterprise contracts were recognized.",
            "status": "answered",
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "answered"
    assert "enterprise contracts" in patch_response.json()["response"]


def test_pagination(client) -> None:
    """Create 5 cases -> GET /cases?skip=2&limit=2 -> assert exactly 2 returned."""
    for i in range(5):
        _create_case(client, name=f"Pagination Case {i}")

    all_response = client.get("/api/v1/cases")
    assert len(all_response.json()) == 5

    paginated_response = client.get("/api/v1/cases?skip=2&limit=2")
    assert paginated_response.status_code == 200
    assert len(paginated_response.json()) == 2


def test_download_export(client) -> None:
    """Create run + export -> GET download -> assert ZIP content-type."""
    case_id = _create_case(client, name="Download Export Test")

    client.post(f"/api/v1/cases/{case_id}/checklist/seed")
    for item in client.get(f"/api/v1/cases/{case_id}/checklist").json():
        client.patch(
            f"/api/v1/cases/{case_id}/checklist/{item['id']}",
            json={"status": "satisfied", "owner": "Test Lead"},
        )

    client.post(
        f"/api/v1/cases/{case_id}/approvals/review",
        json={"reviewer": "IC Reviewer"},
    )

    run_response = client.post(
        f"/api/v1/cases/{case_id}/runs",
        json={"requested_by": "Operator"},
    )
    run_id = run_response.json()["run"]["id"]

    export_response = client.post(
        f"/api/v1/cases/{case_id}/runs/{run_id}/export-package",
        json={"requested_by": "Operator", "title": "Download Test"},
    )
    assert export_response.status_code == 201
    package_id = export_response.json()["id"]

    download_response = client.get(
        f"/api/v1/cases/{case_id}/runs/{run_id}/export-packages/{package_id}/download"
    )
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/zip"
    assert len(download_response.content) > 0


def test_404_on_nonexistent_resources(client) -> None:
    """Verify 404 on GET/PATCH/DELETE for non-existent resources."""
    case_id = _create_case(client, name="404 Test Case")
    fake_id = "00000000-0000-0000-0000-000000000000"

    # Non-existent case
    assert (
        client.patch(f"/api/v1/cases/{fake_id}", json={"name": "Not Found Case"}).status_code == 404
    )
    assert client.delete(f"/api/v1/cases/{fake_id}").status_code == 404

    # Non-existent sub-resources
    assert client.get(f"/api/v1/cases/{case_id}/documents/{fake_id}").status_code == 404
    assert client.get(f"/api/v1/cases/{case_id}/evidence/{fake_id}").status_code == 404
    assert client.get(f"/api/v1/cases/{case_id}/issues/{fake_id}").status_code == 404
    assert client.delete(f"/api/v1/cases/{case_id}/documents/{fake_id}").status_code == 404
    assert client.delete(f"/api/v1/cases/{case_id}/issues/{fake_id}").status_code == 404
