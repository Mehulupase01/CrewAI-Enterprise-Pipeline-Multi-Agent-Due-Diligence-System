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

    issue_response = client.post(
        f"/api/v1/cases/{case_id}/issues",
        json={
            "title": "Unreconciled deferred revenue movement",
            "summary": "Monthly movement does not reconcile cleanly to annual audited balances.",
            "severity": "high",
            "workstream_domain": "financial_qoe",
            "business_impact": "May affect normalized ARR quality and working capital assumptions.",
            "recommended_action": "Obtain a month-by-month revenue waterfall and contract sample.",
            "confidence": 0.86,
            "status": "open",
        },
    )
    assert issue_response.status_code == 201

    detail_response = client.get(f"/api/v1/cases/{case_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["motion_pack"] == "buy_side_diligence"
    assert len(detail_payload["documents"]) == 1
    assert len(detail_payload["evidence_items"]) == 1
    assert len(detail_payload["issues"]) == 1
    assert len(detail_payload["request_items"]) == 1
    assert len(detail_payload["qa_items"]) == 1
    assert detail_payload["evidence_items"][0]["workstream_domain"] == "financial_qoe"


def test_case_detail_returns_404_for_unknown_case(client) -> None:
    response = client.get("/api/v1/cases/non-existent-case")
    assert response.status_code == 404


def test_document_upload_stores_file_and_generates_evidence(client) -> None:
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Cedar",
            "target_name": "CedarWorks Private Limited",
            "summary": "Upload flow validation case.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case_response.json()["id"]

    upload_response = client.post(
        f"/api/v1/cases/{case_id}/documents/upload",
        data={
            "document_kind": "management_memo",
            "source_kind": "uploaded_dataroom",
            "workstream_domain": "financial_qoe",
            "title": "Management memo",
            "evidence_kind": "fact",
        },
        files={
            "file": (
                "memo.txt",
                b"Revenue grew 32 percent year over year.\n\n"
                b"Gross margin improved to 71 percent after cloud optimization.",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 201
    payload = upload_response.json()
    assert payload["artifact"]["processing_status"] == "parsed"
    assert payload["artifact"]["storage_path"].startswith("file:///")
    assert payload["artifact"]["sha256_digest"]
    assert payload["evidence_items_created"] >= 1
    assert payload["parser_name"] == "plaintext"
    assert payload["storage_backend"] == "local"

    evidence_response = client.get(f"/api/v1/cases/{case_id}/evidence")
    assert evidence_response.status_code == 200
    assert len(evidence_response.json()) >= 1


def test_issue_scan_creates_flags_from_evidence(client) -> None:
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Lotus",
            "target_name": "Lotus Grid Services Private Limited",
            "summary": "Issue scan validation case.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case_response.json()["id"]

    evidence_response = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={
            "title": "GST notice summary",
            "evidence_kind": "risk",
            "workstream_domain": "tax",
            "citation": "CBIC notice pack FY25",
            "excerpt": (
                "The company received a GST notice seeking additional tax demand for "
                "input credit reversals in two states."
            ),
            "confidence": 0.92,
        },
    )
    assert evidence_response.status_code == 201

    scan_response = client.post(f"/api/v1/cases/{case_id}/issues/scan")
    assert scan_response.status_code == 201
    scan_payload = scan_response.json()
    assert scan_payload["created_count"] == 1
    assert scan_payload["issues"][0]["severity"] == "high"
    assert scan_payload["issues"][0]["workstream_domain"] == "tax"

    rerun_response = client.post(f"/api/v1/cases/{case_id}/issues/scan")
    assert rerun_response.status_code == 201
    rerun_payload = rerun_response.json()
    assert rerun_payload["created_count"] == 0
    assert rerun_payload["reused_count"] == 1


def test_checklist_seed_and_coverage_summary(client) -> None:
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Summit",
            "target_name": "Summit Cloud Private Limited",
            "summary": "Checklist and coverage validation case.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case_response.json()["id"]

    seed_response = client.post(f"/api/v1/cases/{case_id}/checklist/seed")
    assert seed_response.status_code == 201
    seed_payload = seed_response.json()
    assert seed_payload["created_count"] >= 8
    assert len(seed_payload["checklist_items"]) >= 8

    first_item = seed_payload["checklist_items"][0]
    update_response = client.patch(
        f"/api/v1/cases/{case_id}/checklist/{first_item['id']}",
        json={
            "status": "satisfied",
            "owner": "Finance Lead",
            "note": "Audited statements uploaded and reconciled to management bridge.",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "satisfied"

    coverage_response = client.get(f"/api/v1/cases/{case_id}/coverage")
    assert coverage_response.status_code == 200
    coverage_payload = coverage_response.json()
    assert coverage_payload["total_items"] >= 8
    assert coverage_payload["completed_items"] == 1
    assert coverage_payload["completion_ready"] is False
    assert coverage_payload["open_mandatory_items"] >= 1

    rerun_response = client.post(f"/api/v1/cases/{case_id}/checklist/seed")
    assert rerun_response.status_code == 201
    rerun_payload = rerun_response.json()
    assert rerun_payload["created_count"] == 0
    assert rerun_payload["reused_count"] == seed_payload["created_count"]


def test_approval_review_and_executive_memo(client) -> None:
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Atlas",
            "target_name": "Atlas Payments Private Limited",
            "summary": "Approval and report validation case.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case_response.json()["id"]

    seed_response = client.post(f"/api/v1/cases/{case_id}/checklist/seed")
    assert seed_response.status_code == 201

    issue_response = client.post(
        f"/api/v1/cases/{case_id}/issues",
        json={
            "title": "Outstanding GST exposure",
            "summary": "A pending GST demand remains unresolved in two states.",
            "severity": "high",
            "workstream_domain": "tax",
            "business_impact": "Could require escrow, indemnity, or pricing adjustment.",
            "recommended_action": "Collect notice responses and quantify cash exposure.",
            "confidence": 0.9,
            "status": "open",
        },
    )
    assert issue_response.status_code == 201

    request_response = client.post(
        f"/api/v1/cases/{case_id}/requests",
        json={
            "title": "Upload GST demand papers",
            "detail": "Need all notices, replies, and payment challans for open GST matters.",
            "owner": "Tax Controller",
            "status": "open",
        },
    )
    assert request_response.status_code == 201

    approval_response = client.post(
        f"/api/v1/cases/{case_id}/approvals/review",
        json={
            "reviewer": "IC Reviewer",
            "note": "Case blocked until coverage and tax exposure are resolved.",
        },
    )
    assert approval_response.status_code == 201
    approval_payload = approval_response.json()
    assert approval_payload["decision"] == "changes_requested"
    assert approval_payload["ready_for_export"] is False
    assert approval_payload["open_mandatory_items"] >= 1
    assert approval_payload["blocking_issue_count"] == 1

    report_response = client.get(f"/api/v1/cases/{case_id}/reports/executive-memo")
    assert report_response.status_code == 200
    report_payload = report_response.json()
    assert report_payload["report_status"] == "not_ready"
    assert report_payload["approval_state"] == "changes_requested"
    assert report_payload["checklist_coverage"]["open_mandatory_items"] >= 1
    assert len(report_payload["top_issues"]) >= 1
    assert len(report_payload["open_requests"]) >= 1


def test_workflow_run_generates_traces_and_report_bundles(client) -> None:
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Horizon",
            "target_name": "Horizon Analytics Private Limited",
            "summary": "Workflow execution validation case.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case_response.json()["id"]

    seed_response = client.post(f"/api/v1/cases/{case_id}/checklist/seed")
    assert seed_response.status_code == 201

    issue_response = client.post(
        f"/api/v1/cases/{case_id}/issues",
        json={
            "title": "Customer concentration exposure",
            "summary": "One enterprise client contributes 41 percent of ARR.",
            "severity": "medium",
            "workstream_domain": "commercial",
            "business_impact": "Revenue downside is meaningful if renewal slips.",
            "recommended_action": "Stress test the forecast and review renewal protections.",
            "confidence": 0.84,
            "status": "open",
        },
    )
    assert issue_response.status_code == 201

    request_response = client.post(
        f"/api/v1/cases/{case_id}/requests",
        json={
            "title": "Share customer renewal deck",
            "detail": "Need top ten customer contract terms and renewal history.",
            "owner": "Commercial Lead",
            "status": "open",
        },
    )
    assert request_response.status_code == 201

    run_response = client.post(
        f"/api/v1/cases/{case_id}/runs",
        json={
            "requested_by": "Diligence Operator",
            "note": "Generate current state memo and issue pack.",
        },
    )
    assert run_response.status_code == 201
    run_payload = run_response.json()
    assert run_payload["run"]["status"] == "completed"
    assert len(run_payload["run"]["trace_events"]) >= 5
    assert len(run_payload["run"]["report_bundles"]) == 2
    assert run_payload["executive_memo"]["case_id"] == case_id

    list_response = client.get(f"/api/v1/cases/{case_id}/runs")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    run_id = run_payload["run"]["id"]
    detail_response = client.get(f"/api/v1/cases/{case_id}/runs/{run_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    bundle_kinds = {bundle["bundle_kind"] for bundle in detail_payload["report_bundles"]}
    assert "executive_memo_markdown" in bundle_kinds
    assert "issue_register_markdown" in bundle_kinds
