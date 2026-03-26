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
    assert len(run_payload["run"]["trace_events"]) >= 6
    assert len(run_payload["run"]["report_bundles"]) == 3
    assert len(run_payload["run"]["workstream_syntheses"]) >= 4
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
    assert "workstream_synthesis_markdown" in bundle_kinds
    synthesis_domains = {
        synthesis["workstream_domain"]
        for synthesis in detail_payload["workstream_syntheses"]
    }
    assert "financial_qoe" in synthesis_domains
    assert "commercial" in synthesis_domains


def test_credit_lending_checklist_seed_uses_credit_templates(client) -> None:
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Monsoon Credit Review",
            "target_name": "Monsoon Commerce Private Limited",
            "summary": "Credit pack checklist validation case.",
            "motion_pack": "credit_lending",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case_response.json()["id"]

    seed_response = client.post(f"/api/v1/cases/{case_id}/checklist/seed")
    assert seed_response.status_code == 201
    seed_payload = seed_response.json()
    template_keys = {
        item["template_key"] for item in seed_payload["checklist_items"] if item["template_key"]
    }
    assert "financial_qoe.debt_service_capacity" in template_keys
    assert "legal_corporate.security_package" in template_keys
    assert "forensic.end_use_and_fund_flow" in template_keys
    assert "commercial.customer_concentration" in template_keys


def test_credit_lending_report_uses_credit_memo_language(client) -> None:
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Banyan Working Capital Line",
            "target_name": "Banyan Workflow Systems Private Limited",
            "summary": "Credit memo report validation case.",
            "motion_pack": "credit_lending",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case_response.json()["id"]

    seed_response = client.post(f"/api/v1/cases/{case_id}/checklist/seed")
    assert seed_response.status_code == 201
    for item in seed_response.json()["checklist_items"]:
        update_response = client.patch(
            f"/api/v1/cases/{case_id}/checklist/{item['id']}",
            json={
                "status": "satisfied",
                "owner": "Credit Analyst",
                "note": "Validated for the credit memo test case.",
            },
        )
        assert update_response.status_code == 200

    evidence_response = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={
            "title": "Debt service coverage summary",
            "evidence_kind": "metric",
            "workstream_domain": "financial_qoe",
            "citation": "Underwriting model FY26 base case",
            "excerpt": "Debt service coverage remained above 1.8x with stable collections.",
            "confidence": 0.89,
        },
    )
    assert evidence_response.status_code == 201

    approval_response = client.post(
        f"/api/v1/cases/{case_id}/approvals/review",
        json={
            "reviewer": "Credit Committee",
            "note": "Credit pack should now be export ready.",
        },
    )
    assert approval_response.status_code == 201
    assert approval_response.json()["decision"] == "approved"

    report_response = client.get(f"/api/v1/cases/{case_id}/reports/executive-memo")
    assert report_response.status_code == 200
    report_payload = report_response.json()
    assert report_payload["report_title"] == "Credit Memo"
    assert report_payload["motion_pack"] == "credit_lending"
    assert "underwriting checklist items" in report_payload["executive_summary"]


def test_vendor_onboarding_checklist_seed_uses_vendor_templates(client) -> None:
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Copper Vendor Onboarding",
            "target_name": "Copper Cloud Services Private Limited",
            "summary": "Vendor onboarding checklist validation case.",
            "motion_pack": "vendor_onboarding",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case_response.json()["id"]

    seed_response = client.post(f"/api/v1/cases/{case_id}/checklist/seed")
    assert seed_response.status_code == 201
    seed_payload = seed_response.json()
    template_keys = {
        item["template_key"] for item in seed_payload["checklist_items"] if item["template_key"]
    }
    assert "legal_corporate.vendor_registration" in template_keys
    assert "regulatory.vendor_restrictions" in template_keys
    assert "forensic.third_party_integrity" in template_keys
    assert "cyber_privacy.vendor_security_posture" in template_keys


def test_vendor_onboarding_report_uses_third_party_risk_memo_language(client) -> None:
    case_response = client.post(
        "/api/v1/cases",
        json={
            "name": "Project Delta Vendor Approval",
            "target_name": "Delta Automation Services Private Limited",
            "summary": "Third-party risk memo validation case.",
            "motion_pack": "vendor_onboarding",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_id = case_response.json()["id"]

    seed_response = client.post(f"/api/v1/cases/{case_id}/checklist/seed")
    assert seed_response.status_code == 201
    for item in seed_response.json()["checklist_items"]:
        update_response = client.patch(
            f"/api/v1/cases/{case_id}/checklist/{item['id']}",
            json={
                "status": "satisfied",
                "owner": "Third-Party Risk Analyst",
                "note": "Validated for the vendor memo test case.",
            },
        )
        assert update_response.status_code == 200

    evidence_response = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={
            "title": "Vendor security questionnaire summary",
            "evidence_kind": "fact",
            "workstream_domain": "cyber_privacy",
            "citation": "Vendor security questionnaire v3",
            "excerpt": "No material security control gaps or sanctions alerts were identified.",
            "confidence": 0.9,
        },
    )
    assert evidence_response.status_code == 201

    approval_response = client.post(
        f"/api/v1/cases/{case_id}/approvals/review",
        json={
            "reviewer": "Vendor Approval Board",
            "note": "Third-party risk memo should now be export ready.",
        },
    )
    assert approval_response.status_code == 201
    assert approval_response.json()["decision"] == "approved"

    report_response = client.get(f"/api/v1/cases/{case_id}/reports/executive-memo")
    assert report_response.status_code == 200
    report_payload = report_response.json()
    assert report_payload["report_title"] == "Third-Party Risk Memo"
    assert report_payload["motion_pack"] == "vendor_onboarding"
    assert "third-party risk items" in report_payload["executive_summary"]
