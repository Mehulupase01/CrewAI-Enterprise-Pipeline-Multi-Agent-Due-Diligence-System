from __future__ import annotations

import argparse
import asyncio
import json
import os
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi.testclient import TestClient

from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.db.session import close_database
from crewai_enterprise_pipeline_api.evaluation.scenarios import (
    EVALUATION_SUITES,
    ChecklistUpdateFixture,
    EvaluationScenario,
    EvaluationSuiteDefinition,
)

DEFAULT_BUNDLE_KINDS = {
    "executive_memo_markdown",
    "issue_register_markdown",
    "workstream_synthesis_markdown",
}
PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "evaluations"
ENV_KEYS = (
    "DATABASE_URL",
    "APP_ENV",
    "AUTO_CREATE_SCHEMA",
    "STORAGE_BACKEND",
    "LOCAL_STORAGE_ROOT",
)


def _ensure_success(step: str, response, expected_status: int) -> dict[str, Any]:
    if response.status_code != expected_status:
        raise RuntimeError(f"{step} failed with status {response.status_code}: {response.text}")
    return response.json()


def _append_check(
    checks: list[dict[str, Any]],
    *,
    name: str,
    passed: bool,
    actual: Any,
    expected: Any,
    detail: str,
) -> None:
    checks.append(
        {
            "name": name,
            "passed": passed,
            "actual": actual,
            "expected": expected,
            "detail": detail,
        }
    )


@contextmanager
def _isolated_client(runtime_root: Path):
    previous_env = {key: os.environ.get(key) for key in ENV_KEYS}
    runtime_root.mkdir(parents=True, exist_ok=True)
    storage_root = runtime_root / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)

    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(runtime_root / 'eval.db').as_posix()}"
    os.environ["APP_ENV"] = "test"
    os.environ["AUTO_CREATE_SCHEMA"] = "true"
    os.environ["STORAGE_BACKEND"] = "local"
    os.environ["LOCAL_STORAGE_ROOT"] = str(storage_root.resolve())
    get_settings.cache_clear()

    from crewai_enterprise_pipeline_api.main import create_app

    try:
        with TestClient(create_app()) as client:
            yield client
    finally:
        get_settings.cache_clear()
        asyncio.run(close_database())
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _update_all_checklist_items(client: TestClient, case_id: str, checklist_items) -> None:
    for item in checklist_items:
        response = client.patch(
            f"/api/v1/cases/{case_id}/checklist/{item['id']}",
            json={
                "status": "satisfied",
                "owner": "Evaluation Runner",
                "note": "Satisfied by the automated evaluation harness.",
            },
        )
        _ensure_success(
            f"update checklist item {item['template_key'] or item['id']}",
            response,
            200,
        )


def _update_checklist_item(
    client: TestClient,
    case_id: str,
    checklist_items,
    update: ChecklistUpdateFixture,
) -> None:
    target = next(
        (item for item in checklist_items if item["template_key"] == update.template_key),
        None,
    )
    if target is None:
        raise RuntimeError(
            f"Checklist template '{update.template_key}' was not found for case {case_id}."
        )

    response = client.patch(
        f"/api/v1/cases/{case_id}/checklist/{target['id']}",
        json=update.payload,
    )
    _ensure_success(f"patch checklist template {update.template_key}", response, 200)


def _evaluate_scenario(scenario: EvaluationScenario) -> dict[str, Any]:
    with TemporaryDirectory(prefix=f"{scenario.code}-") as temp_dir:
        with _isolated_client(Path(temp_dir)) as client:
            case_payload = _ensure_success(
                "create case",
                client.post("/api/v1/cases", json=scenario.case_payload),
                201,
            )
            case_id = case_payload["id"]

            seeded = _ensure_success(
                "seed checklist",
                client.post(f"/api/v1/cases/{case_id}/checklist/seed"),
                201,
            )
            checklist_items = seeded["checklist_items"]

            if scenario.satisfy_all_checklist_items:
                _update_all_checklist_items(client, case_id, checklist_items)

            for update in scenario.checklist_updates:
                _update_checklist_item(client, case_id, checklist_items, update)

            for upload in scenario.upload_documents:
                file_bytes = (
                    upload.content_bytes
                    if upload.content_bytes is not None
                    else upload.content.encode("utf-8")
                )
                response = client.post(
                    f"/api/v1/cases/{case_id}/documents/upload",
                    data={
                        "document_kind": upload.document_kind,
                        "source_kind": upload.source_kind,
                        "workstream_domain": upload.workstream_domain,
                        "title": upload.title,
                        "evidence_kind": upload.evidence_kind,
                    },
                    files={
                        "file": (
                            upload.filename,
                            file_bytes,
                            upload.mime_type,
                        )
                    },
                )
                _ensure_success(f"upload document {upload.filename}", response, 201)

            for evidence in scenario.evidence_items:
                response = client.post(
                    f"/api/v1/cases/{case_id}/evidence",
                    json=evidence.payload,
                )
                _ensure_success(
                    f"create evidence {evidence.payload['title']}",
                    response,
                    201,
                )

            issue_scan_first: dict[str, Any] | None = None
            issue_scan_second: dict[str, Any] | None = None
            if scenario.scan_issues:
                issue_scan_first = _ensure_success(
                    "scan issues",
                    client.post(f"/api/v1/cases/{case_id}/issues/scan"),
                    201,
                )
                issue_scan_second = _ensure_success(
                    "re-scan issues",
                    client.post(f"/api/v1/cases/{case_id}/issues/scan"),
                    201,
                )

            for issue in scenario.issues:
                response = client.post(f"/api/v1/cases/{case_id}/issues", json=issue.payload)
                _ensure_success(f"create issue {issue.payload['title']}", response, 201)

            for request in scenario.requests:
                response = client.post(
                    f"/api/v1/cases/{case_id}/requests",
                    json=request.payload,
                )
                _ensure_success(
                    f"create request {request.payload['title']}",
                    response,
                    201,
                )

            for qa_item in scenario.qa_items:
                response = client.post(f"/api/v1/cases/{case_id}/qa", json=qa_item.payload)
                _ensure_success("create q&a item", response, 201)

            financial_summary: dict[str, Any] | None = None
            if scenario.financial_summary_expectation is not None:
                financial_summary = _ensure_success(
                    "financial summary",
                    client.get(f"/api/v1/cases/{case_id}/financial-summary"),
                    200,
                )
            legal_summary: dict[str, Any] | None = None
            if scenario.legal_summary_expectation is not None:
                legal_summary = _ensure_success(
                    "legal summary",
                    client.get(f"/api/v1/cases/{case_id}/legal-summary"),
                    200,
                )
            tax_summary: dict[str, Any] | None = None
            if scenario.tax_summary_expectation is not None:
                tax_summary = _ensure_success(
                    "tax summary",
                    client.get(f"/api/v1/cases/{case_id}/tax-summary"),
                    200,
                )
            compliance_matrix: list[dict[str, Any]] | None = None
            if scenario.compliance_matrix_expectation is not None:
                compliance_matrix = _ensure_success(
                    "compliance matrix",
                    client.get(f"/api/v1/cases/{case_id}/compliance-matrix"),
                    200,
                )
            commercial_summary: dict[str, Any] | None = None
            if scenario.commercial_summary_expectation is not None:
                commercial_summary = _ensure_success(
                    "commercial summary",
                    client.get(f"/api/v1/cases/{case_id}/commercial-summary"),
                    200,
                )
            operations_summary: dict[str, Any] | None = None
            if scenario.operations_summary_expectation is not None:
                operations_summary = _ensure_success(
                    "operations summary",
                    client.get(f"/api/v1/cases/{case_id}/operations-summary"),
                    200,
                )
            cyber_summary: dict[str, Any] | None = None
            if scenario.cyber_summary_expectation is not None:
                cyber_summary = _ensure_success(
                    "cyber summary",
                    client.get(f"/api/v1/cases/{case_id}/cyber-summary"),
                    200,
                )
            forensic_flags: list[dict[str, Any]] | None = None
            if scenario.forensic_summary_expectation is not None:
                forensic_flags = _ensure_success(
                    "forensic flags",
                    client.get(f"/api/v1/cases/{case_id}/forensic-flags"),
                    200,
                )
            buy_side_analysis: dict[str, Any] | None = None
            if scenario.buy_side_analysis_expectation is not None:
                buy_side_analysis = _ensure_success(
                    "buy-side analysis",
                    client.get(f"/api/v1/cases/{case_id}/buy-side-analysis"),
                    200,
                )
            borrower_scorecard: dict[str, Any] | None = None
            if scenario.borrower_scorecard_expectation is not None:
                borrower_scorecard = _ensure_success(
                    "borrower scorecard",
                    client.get(f"/api/v1/cases/{case_id}/borrower-scorecard"),
                    200,
                )
            vendor_risk_tier: dict[str, Any] | None = None
            if scenario.vendor_risk_tier_expectation is not None:
                vendor_risk_tier = _ensure_success(
                    "vendor risk tier",
                    client.get(f"/api/v1/cases/{case_id}/vendor-risk-tier"),
                    200,
                )
            tech_saas_metrics: dict[str, Any] | None = None
            if scenario.tech_saas_metrics_expectation is not None:
                tech_saas_metrics = _ensure_success(
                    "tech saas metrics",
                    client.get(f"/api/v1/cases/{case_id}/tech-saas-metrics"),
                    200,
                )
            manufacturing_metrics: dict[str, Any] | None = None
            if scenario.manufacturing_metrics_expectation is not None:
                manufacturing_metrics = _ensure_success(
                    "manufacturing metrics",
                    client.get(f"/api/v1/cases/{case_id}/manufacturing-metrics"),
                    200,
                )
            bfsi_nbfc_metrics: dict[str, Any] | None = None
            if scenario.bfsi_nbfc_metrics_expectation is not None:
                bfsi_nbfc_metrics = _ensure_success(
                    "bfsi nbfc metrics",
                    client.get(f"/api/v1/cases/{case_id}/bfsi-nbfc-metrics"),
                    200,
                )

            approval = _ensure_success(
                "approval review",
                client.post(
                    f"/api/v1/cases/{case_id}/approvals/review",
                    json=scenario.approval_payload,
                ),
                201,
            )
            executive_memo = _ensure_success(
                "executive memo",
                client.get(f"/api/v1/cases/{case_id}/reports/executive-memo"),
                200,
            )
            run_result = _ensure_success(
                "execute run",
                client.post(
                    f"/api/v1/cases/{case_id}/runs",
                    json=scenario.run_payload,
                ),
                201,
            )
            run = run_result["run"]
            run_detail = _ensure_success(
                "fetch run detail",
                client.get(f"/api/v1/cases/{case_id}/runs/{run['id']}"),
                200,
            )
            export_package: dict[str, Any] | None = None
            if scenario.rich_reporting_expectation is not None:
                export_package = _ensure_success(
                    "create export package",
                    client.post(
                        f"/api/v1/cases/{case_id}/runs/{run['id']}/export-package",
                        json={
                            "requested_by": "Evaluation Runner",
                            "title": "Evaluation Rich Reporting Export",
                            "include_json_snapshot": True,
                        },
                    ),
                    201,
                )
            coverage = _ensure_success(
                "coverage summary",
                client.get(f"/api/v1/cases/{case_id}/coverage"),
                200,
            )
            case_detail = _ensure_success(
                "case detail",
                client.get(f"/api/v1/cases/{case_id}"),
                200,
            )

    issue_severities = sorted({issue["severity"] for issue in case_detail["issues"]})
    bundle_kinds = sorted({bundle["bundle_kind"] for bundle in run_detail["report_bundles"]})
    open_request_count = sum(
        1 for item in case_detail["request_items"] if item["status"] != "closed"
    )
    metrics = {
        "case_id": case_id,
        "document_count": len(case_detail["documents"]),
        "evidence_count": len(case_detail["evidence_items"]),
        "issue_count": len(case_detail["issues"]),
        "issue_severities": issue_severities,
        "open_request_count": open_request_count,
        "open_mandatory_items": coverage["open_mandatory_items"],
        "blocking_issue_count": approval["blocking_issue_count"],
        "trace_event_count": len(run_detail["trace_events"]),
        "report_bundle_count": len(run_detail["report_bundles"]),
        "workstream_synthesis_count": len(run_detail["workstream_syntheses"]),
        "bundle_kinds": bundle_kinds,
    }
    if export_package is not None:
        metrics["export_included_files"] = export_package["included_files"]
        metrics["export_byte_size"] = export_package["byte_size"]
    if financial_summary is not None:
        metrics["financial_period_count"] = len(financial_summary["periods"])
        metrics["financial_flag_count"] = len(financial_summary["flags"])
        metrics["financial_checklist_update_count"] = len(
            financial_summary.get("checklist_updates", [])
        )
    if legal_summary is not None:
        metrics["legal_director_count"] = len(legal_summary["directors"])
        metrics["legal_contract_review_count"] = len(legal_summary["contract_reviews"])
        metrics["legal_checklist_update_count"] = len(legal_summary.get("checklist_updates", []))
    if tax_summary is not None:
        metrics["tax_known_status_count"] = len(
            [item for item in tax_summary["items"] if item["status"] != "unknown"]
        )
        metrics["tax_gstin_count"] = len(tax_summary["gstins"])
        metrics["tax_checklist_update_count"] = len(tax_summary.get("checklist_updates", []))
    if compliance_matrix is not None:
        metrics["compliance_item_count"] = len(compliance_matrix)
        metrics["compliance_known_status_count"] = len(
            [item for item in compliance_matrix if item["status"] != "unknown"]
        )
    if commercial_summary is not None:
        metrics["commercial_concentration_count"] = len(commercial_summary["concentration_signals"])
        metrics["commercial_checklist_update_count"] = len(
            commercial_summary.get("checklist_updates", [])
        )
    if operations_summary is not None:
        metrics["operations_dependency_count"] = len(operations_summary["dependency_signals"])
        metrics["operations_checklist_update_count"] = len(
            operations_summary.get("checklist_updates", [])
        )
    if cyber_summary is not None:
        metrics["cyber_known_control_count"] = len(
            [item for item in cyber_summary["controls"] if item["status"] != "unknown"]
        )
        metrics["cyber_checklist_update_count"] = len(cyber_summary.get("checklist_updates", []))
        metrics["cyber_breach_history_count"] = len(cyber_summary["breach_history"])
    if forensic_flags is not None:
        metrics["forensic_flag_count"] = len(forensic_flags)
    if buy_side_analysis is not None:
        metrics["buy_side_valuation_bridge_count"] = len(buy_side_analysis["valuation_bridge"])
        metrics["buy_side_spa_issue_count"] = len(buy_side_analysis["spa_issues"])
        metrics["buy_side_pmi_risk_count"] = len(buy_side_analysis["pmi_risks"])
        metrics["buy_side_checklist_update_count"] = len(
            buy_side_analysis.get("checklist_updates", [])
        )
    if borrower_scorecard is not None:
        metrics["borrower_scorecard_overall_score"] = borrower_scorecard["overall_score"]
        metrics["borrower_covenant_item_count"] = len(borrower_scorecard["covenant_tracking"])
        metrics["borrower_checklist_update_count"] = len(
            borrower_scorecard.get("checklist_updates", [])
        )
    if vendor_risk_tier is not None:
        metrics["vendor_tier_overall_score"] = vendor_risk_tier["overall_score"]
        metrics["vendor_tier_questionnaire_count"] = len(vendor_risk_tier["questionnaire"])
        metrics["vendor_tier_checklist_update_count"] = len(
            vendor_risk_tier.get("checklist_updates", [])
        )
    if tech_saas_metrics is not None:
        metrics["tech_saas_arr_waterfall_count"] = len(tech_saas_metrics["arr_waterfall"])
        metrics["tech_saas_checklist_update_count"] = len(
            tech_saas_metrics.get("checklist_updates", [])
        )
    if manufacturing_metrics is not None:
        metrics["manufacturing_asset_register_count"] = len(manufacturing_metrics["asset_register"])
        metrics["manufacturing_checklist_update_count"] = len(
            manufacturing_metrics.get("checklist_updates", [])
        )
    if bfsi_nbfc_metrics is not None:
        metrics["bfsi_alm_bucket_count"] = len(bfsi_nbfc_metrics["alm_bucket_gaps"])
        metrics["bfsi_checklist_update_count"] = len(
            bfsi_nbfc_metrics.get("checklist_updates", [])
        )

    checks: list[dict[str, Any]] = []
    expectation = scenario.expectation
    _append_check(
        checks,
        name="approval_decision",
        passed=approval["decision"] == expectation.approval_decision,
        actual=approval["decision"],
        expected=expectation.approval_decision,
        detail="Approval decision should match the scenario expectation.",
    )
    _append_check(
        checks,
        name="ready_for_export",
        passed=approval["ready_for_export"] == expectation.ready_for_export,
        actual=approval["ready_for_export"],
        expected=expectation.ready_for_export,
        detail="Reviewer readiness should match the expected export state.",
    )
    _append_check(
        checks,
        name="report_status",
        passed=executive_memo["report_status"] == expectation.report_status,
        actual=executive_memo["report_status"],
        expected=expectation.report_status,
        detail="Memo status should reflect approval readiness.",
    )
    _append_check(
        checks,
        name="run_completed",
        passed=run_detail["status"] == "completed",
        actual=run_detail["status"],
        expected="completed",
        detail="Workflow runs must complete successfully during evaluation.",
    )
    _append_check(
        checks,
        name="trace_event_count",
        passed=metrics["trace_event_count"] >= expectation.min_trace_events,
        actual=metrics["trace_event_count"],
        expected=f">= {expectation.min_trace_events}",
        detail="Each run should emit the expected trace depth.",
    )
    _append_check(
        checks,
        name="report_bundle_count",
        passed=metrics["report_bundle_count"] >= expectation.min_report_bundles,
        actual=metrics["report_bundle_count"],
        expected=f">= {expectation.min_report_bundles}",
        detail="Each run should generate the core report bundles.",
    )
    _append_check(
        checks,
        name="workstream_synthesis_count",
        passed=metrics["workstream_synthesis_count"] >= expectation.min_syntheses,
        actual=metrics["workstream_synthesis_count"],
        expected=f">= {expectation.min_syntheses}",
        detail="The relevant workstream syntheses should be persisted.",
    )
    _append_check(
        checks,
        name="issue_count",
        passed=metrics["issue_count"] >= expectation.min_issue_count,
        actual=metrics["issue_count"],
        expected=f">= {expectation.min_issue_count}",
        detail="Scenario issue volume should meet the expected minimum.",
    )
    _append_check(
        checks,
        name="open_request_count",
        passed=metrics["open_request_count"] >= expectation.min_open_request_count,
        actual=metrics["open_request_count"],
        expected=f">= {expectation.min_open_request_count}",
        detail="Open request tracking should reflect the scenario setup.",
    )
    _append_check(
        checks,
        name="evidence_count",
        passed=metrics["evidence_count"] >= expectation.min_evidence_count,
        actual=metrics["evidence_count"],
        expected=f">= {expectation.min_evidence_count}",
        detail="Evidence extraction should create the expected minimum volume.",
    )
    _append_check(
        checks,
        name="bundle_kinds",
        passed=set(expectation.expected_bundle_kinds).issubset(bundle_kinds),
        actual=bundle_kinds,
        expected=list(expectation.expected_bundle_kinds),
        detail="Core markdown bundle types should always be present.",
    )
    if scenario.rich_reporting_expectation is not None:
        rich_expectation = scenario.rich_reporting_expectation
        _append_check(
            checks,
            name="report_template",
            passed=run_detail["report_template"] == rich_expectation.report_template,
            actual=run_detail["report_template"],
            expected=rich_expectation.report_template,
            detail="Rich reporting scenarios should persist the requested template on the run.",
        )
        _append_check(
            checks,
            name="export_files",
            passed=set(rich_expectation.required_export_files).issubset(
                set(metrics.get("export_included_files", []))
            ),
            actual=metrics.get("export_included_files", []),
            expected=list(rich_expectation.required_export_files),
            detail=(
                "Export packages should include the rich reporting markdown, DOCX, "
                "and PDF artifacts."
            ),
        )

    if expectation.report_title is not None:
        _append_check(
            checks,
            name="report_title",
            passed=executive_memo["report_title"] == expectation.report_title,
            actual=executive_memo["report_title"],
            expected=expectation.report_title,
            detail="Motion-specific memo title should match the scenario expectation.",
        )
    if expectation.open_mandatory_items is not None:
        _append_check(
            checks,
            name="open_mandatory_items",
            passed=metrics["open_mandatory_items"] == expectation.open_mandatory_items,
            actual=metrics["open_mandatory_items"],
            expected=expectation.open_mandatory_items,
            detail="Checklist coverage should match the scenario expectation.",
        )
    if expectation.min_blocking_issue_count is not None:
        _append_check(
            checks,
            name="min_blocking_issue_count",
            passed=metrics["blocking_issue_count"] >= expectation.min_blocking_issue_count,
            actual=metrics["blocking_issue_count"],
            expected=f">= {expectation.min_blocking_issue_count}",
            detail="Blocking issue count should satisfy the lower bound.",
        )
    if expectation.max_blocking_issue_count is not None:
        _append_check(
            checks,
            name="max_blocking_issue_count",
            passed=metrics["blocking_issue_count"] <= expectation.max_blocking_issue_count,
            actual=metrics["blocking_issue_count"],
            expected=f"<= {expectation.max_blocking_issue_count}",
            detail="Blocking issue count should satisfy the upper bound.",
        )
    if expectation.expected_issue_severities:
        _append_check(
            checks,
            name="issue_severities",
            passed=set(expectation.expected_issue_severities).issubset(issue_severities),
            actual=issue_severities,
            expected=list(expectation.expected_issue_severities),
            detail="Expected issue severities should appear in the register.",
        )
    if issue_scan_second is not None:
        _append_check(
            checks,
            name="issue_scan_idempotent",
            passed=issue_scan_second["created_count"] == 0,
            actual=issue_scan_second["created_count"],
            expected=0,
            detail=(
                "A repeat issue scan should reuse existing fingerprints instead of "
                "duplicating flags."
            ),
        )
    if scenario.financial_summary_expectation is not None and financial_summary is not None:
        fin_expectation = scenario.financial_summary_expectation
        _append_check(
            checks,
            name="financial_period_count",
            passed=len(financial_summary["periods"]) >= fin_expectation.min_periods,
            actual=len(financial_summary["periods"]),
            expected=f">= {fin_expectation.min_periods}",
            detail="Financial QoE endpoint should parse the expected minimum number of periods.",
        )
        if fin_expectation.expected_normalized_ebitda is not None:
            actual_normalized = financial_summary["normalized_ebitda"]
            passed = (
                actual_normalized is not None
                and abs(actual_normalized - fin_expectation.expected_normalized_ebitda) < 0.0001
            )
            _append_check(
                checks,
                name="financial_normalized_ebitda",
                passed=passed,
                actual=actual_normalized,
                expected=fin_expectation.expected_normalized_ebitda,
                detail="Normalized EBITDA should match the expected hand calculation.",
            )
        if fin_expectation.required_ratio_keys:
            actual_ratio_keys = sorted(
                key for key, value in financial_summary["ratios"].items() if value is not None
            )
            _append_check(
                checks,
                name="financial_ratio_keys",
                passed=set(fin_expectation.required_ratio_keys).issubset(actual_ratio_keys),
                actual=actual_ratio_keys,
                expected=list(fin_expectation.required_ratio_keys),
                detail="Required financial ratios should be available in the QoE summary.",
            )
        if fin_expectation.flag_substrings:
            actual_flags = financial_summary["flags"]
            _append_check(
                checks,
                name="financial_flags",
                passed=all(
                    any(fragment.lower() in flag.lower() for flag in actual_flags)
                    for fragment in fin_expectation.flag_substrings
                ),
                actual=actual_flags,
                expected=list(fin_expectation.flag_substrings),
                detail="Expected financial red-flag phrases should appear in the QoE summary.",
            )
            _append_check(
                checks,
                name="financial_checklist_updates",
                passed=len(financial_summary.get("checklist_updates", []))
                >= fin_expectation.min_checklist_updates,
                actual=len(financial_summary.get("checklist_updates", [])),
                expected=f">= {fin_expectation.min_checklist_updates}",
                detail=(
                    "Financial QoE refresh should auto-satisfy the expected minimum "
                    "checklist items."
                ),
            )
    if scenario.legal_summary_expectation is not None and legal_summary is not None:
        legal_expectation = scenario.legal_summary_expectation
        actual_clause_keys = sorted(
            {
                clause["clause_key"]
                for review in legal_summary["contract_reviews"]
                for clause in review["clauses"]
                if clause["present"]
            }
        )
        _append_check(
            checks,
            name="legal_director_count",
            passed=len(legal_summary["directors"]) >= legal_expectation.min_directors,
            actual=len(legal_summary["directors"]),
            expected=f">= {legal_expectation.min_directors}",
            detail="Legal summary should extract the expected minimum number of directors.",
        )
        _append_check(
            checks,
            name="legal_contract_review_count",
            passed=len(legal_summary["contract_reviews"]) >= legal_expectation.min_contract_reviews,
            actual=len(legal_summary["contract_reviews"]),
            expected=f">= {legal_expectation.min_contract_reviews}",
            detail="Contract review extraction should find the expected number of contracts.",
        )
        if legal_expectation.required_clause_keys:
            _append_check(
                checks,
                name="legal_clause_keys",
                passed=set(legal_expectation.required_clause_keys).issubset(actual_clause_keys),
                actual=actual_clause_keys,
                expected=list(legal_expectation.required_clause_keys),
                detail="Required contract clause keys should be present in the legal summary.",
            )
        if legal_expectation.flag_substrings:
            actual_flags = legal_summary["flags"]
            _append_check(
                checks,
                name="legal_flags",
                passed=all(
                    any(fragment.lower() in flag.lower() for flag in actual_flags)
                    for fragment in legal_expectation.flag_substrings
                ),
                actual=actual_flags,
                expected=list(legal_expectation.flag_substrings),
                detail="Expected legal flag phrases should appear in the legal summary.",
            )
        _append_check(
            checks,
            name="legal_checklist_updates",
            passed=len(legal_summary.get("checklist_updates", []))
            >= legal_expectation.min_checklist_updates,
            actual=len(legal_summary.get("checklist_updates", [])),
            expected=f">= {legal_expectation.min_checklist_updates}",
            detail="Legal engine should auto-satisfy the expected minimum checklist items.",
        )
    if scenario.tax_summary_expectation is not None and tax_summary is not None:
        tax_expectation = scenario.tax_summary_expectation
        tax_status_map = {item["tax_area"]: item["status"] for item in tax_summary["items"]}
        actual_tax_areas = sorted(tax_status_map)
        if tax_expectation.required_tax_areas:
            _append_check(
                checks,
                name="tax_areas",
                passed=set(tax_expectation.required_tax_areas).issubset(actual_tax_areas),
                actual=actual_tax_areas,
                expected=list(tax_expectation.required_tax_areas),
                detail="Expected tax areas should be represented in the tax summary.",
            )
        if tax_expectation.required_statuses:
            _append_check(
                checks,
                name="tax_statuses",
                passed=all(
                    tax_status_map.get(area) == status
                    for area, status in tax_expectation.required_statuses.items()
                ),
                actual=tax_status_map,
                expected=tax_expectation.required_statuses,
                detail="Tax statuses should match the expected compliance matrix.",
            )
        _append_check(
            checks,
            name="tax_gstins",
            passed=len(tax_summary["gstins"]) >= tax_expectation.min_gstins,
            actual=len(tax_summary["gstins"]),
            expected=f">= {tax_expectation.min_gstins}",
            detail="Tax summary should extract the expected minimum GSTIN volume.",
        )
        if tax_expectation.flag_substrings:
            actual_flags = tax_summary["flags"]
            _append_check(
                checks,
                name="tax_flags",
                passed=all(
                    any(fragment.lower() in flag.lower() for flag in actual_flags)
                    for fragment in tax_expectation.flag_substrings
                ),
                actual=actual_flags,
                expected=list(tax_expectation.flag_substrings),
                detail="Expected tax flag phrases should appear in the tax summary.",
            )
        _append_check(
            checks,
            name="tax_checklist_updates",
            passed=len(tax_summary.get("checklist_updates", []))
            >= tax_expectation.min_checklist_updates,
            actual=len(tax_summary.get("checklist_updates", [])),
            expected=f">= {tax_expectation.min_checklist_updates}",
            detail="Tax engine should auto-satisfy the expected minimum checklist items.",
        )
    if scenario.compliance_matrix_expectation is not None and compliance_matrix is not None:
        compliance_expectation = scenario.compliance_matrix_expectation
        regulation_status_map = {item["regulation"]: item["status"] for item in compliance_matrix}
        actual_regulations = sorted(regulation_status_map)
        if compliance_expectation.required_regulations:
            _append_check(
                checks,
                name="compliance_regulations",
                passed=set(compliance_expectation.required_regulations).issubset(
                    actual_regulations
                ),
                actual=actual_regulations,
                expected=list(compliance_expectation.required_regulations),
                detail="Compliance matrix should include the expected regulations.",
            )
        if compliance_expectation.required_statuses:
            _append_check(
                checks,
                name="compliance_statuses",
                passed=all(
                    regulation_status_map.get(regulation) == status
                    for regulation, status in compliance_expectation.required_statuses.items()
                ),
                actual=regulation_status_map,
                expected=compliance_expectation.required_statuses,
                detail="Compliance statuses should match the expected matrix outcome.",
            )
        _append_check(
            checks,
            name="compliance_known_statuses",
            passed=metrics["compliance_known_status_count"]
            >= compliance_expectation.min_known_statuses,
            actual=metrics["compliance_known_status_count"],
            expected=f">= {compliance_expectation.min_known_statuses}",
            detail="Compliance matrix should determine the expected minimum number of statuses.",
        )
        if compliance_expectation.flag_substrings:
            actual_notes = [item["notes"] for item in compliance_matrix]
            _append_check(
                checks,
                name="compliance_flags",
                passed=all(
                    any(fragment.lower() in note.lower() for note in actual_notes)
                    for fragment in compliance_expectation.flag_substrings
                ),
                actual=actual_notes,
                expected=list(compliance_expectation.flag_substrings),
                detail="Expected compliance-note phrases should appear in the matrix.",
            )
    if scenario.commercial_summary_expectation is not None and commercial_summary is not None:
        commercial_expectation = scenario.commercial_summary_expectation
        _append_check(
            checks,
            name="commercial_concentration_count",
            passed=len(commercial_summary["concentration_signals"])
            >= commercial_expectation.min_concentration_signals,
            actual=len(commercial_summary["concentration_signals"]),
            expected=f">= {commercial_expectation.min_concentration_signals}",
            detail="Commercial summary should surface the expected concentration depth.",
        )
        if commercial_expectation.expected_top_share is not None:
            actual_top_share = (
                None
                if not commercial_summary["concentration_signals"]
                else commercial_summary["concentration_signals"][0]["share_of_revenue"]
            )
            passed = (
                actual_top_share is not None
                and abs(actual_top_share - commercial_expectation.expected_top_share) < 0.0001
            )
            _append_check(
                checks,
                name="commercial_top_share",
                passed=passed,
                actual=actual_top_share,
                expected=commercial_expectation.expected_top_share,
                detail="Top commercial concentration share should match the expected value.",
            )
        if commercial_expectation.expected_nrr is not None:
            actual_nrr = commercial_summary["net_revenue_retention"]
            passed = (
                actual_nrr is not None
                and abs(actual_nrr - commercial_expectation.expected_nrr) < 0.0001
            )
            _append_check(
                checks,
                name="commercial_nrr",
                passed=passed,
                actual=actual_nrr,
                expected=commercial_expectation.expected_nrr,
                detail="NRR should match the expected commercial extraction.",
            )
        if commercial_expectation.expected_churn is not None:
            actual_churn = commercial_summary["churn_rate"]
            passed = (
                actual_churn is not None
                and abs(actual_churn - commercial_expectation.expected_churn) < 0.0001
            )
            _append_check(
                checks,
                name="commercial_churn",
                passed=passed,
                actual=actual_churn,
                expected=commercial_expectation.expected_churn,
                detail="Churn should match the expected commercial extraction.",
            )
        if commercial_expectation.flag_substrings:
            actual_flags = commercial_summary["flags"]
            _append_check(
                checks,
                name="commercial_flags",
                passed=all(
                    any(fragment.lower() in flag.lower() for flag in actual_flags)
                    for fragment in commercial_expectation.flag_substrings
                ),
                actual=actual_flags,
                expected=list(commercial_expectation.flag_substrings),
                detail="Expected commercial flag phrases should appear in the summary.",
            )
        _append_check(
            checks,
            name="commercial_checklist_updates",
            passed=len(commercial_summary.get("checklist_updates", []))
            >= commercial_expectation.min_checklist_updates,
            actual=len(commercial_summary.get("checklist_updates", [])),
            expected=f">= {commercial_expectation.min_checklist_updates}",
            detail="Commercial engine should auto-satisfy the expected minimum checklist items.",
        )
    if scenario.operations_summary_expectation is not None and operations_summary is not None:
        operations_expectation = scenario.operations_summary_expectation
        _append_check(
            checks,
            name="operations_dependency_count",
            passed=len(operations_summary["dependency_signals"])
            >= operations_expectation.min_dependency_signals,
            actual=len(operations_summary["dependency_signals"]),
            expected=f">= {operations_expectation.min_dependency_signals}",
            detail="Operations summary should surface the expected dependency depth.",
        )
        if operations_expectation.expected_supplier_concentration is not None:
            actual_supplier_concentration = operations_summary["supplier_concentration_top_3"]
            passed = (
                actual_supplier_concentration is not None
                and abs(
                    actual_supplier_concentration
                    - operations_expectation.expected_supplier_concentration
                )
                < 0.0001
            )
            _append_check(
                checks,
                name="operations_supplier_concentration",
                passed=passed,
                actual=actual_supplier_concentration,
                expected=operations_expectation.expected_supplier_concentration,
                detail="Supplier concentration should match the expected extracted value.",
            )
        if operations_expectation.expect_single_site_dependency is not None:
            _append_check(
                checks,
                name="operations_single_site_dependency",
                passed=operations_summary["single_site_dependency"]
                == operations_expectation.expect_single_site_dependency,
                actual=operations_summary["single_site_dependency"],
                expected=operations_expectation.expect_single_site_dependency,
                detail="Single-site dependency should match the expected operations state.",
            )
        _append_check(
            checks,
            name="operations_key_person_dependencies",
            passed=len(operations_summary["key_person_dependencies"])
            >= operations_expectation.min_key_person_dependencies,
            actual=len(operations_summary["key_person_dependencies"]),
            expected=f">= {operations_expectation.min_key_person_dependencies}",
            detail="Operations summary should surface the expected key-person dependency volume.",
        )
        if operations_expectation.flag_substrings:
            actual_flags = operations_summary["flags"]
            _append_check(
                checks,
                name="operations_flags",
                passed=all(
                    any(fragment.lower() in flag.lower() for flag in actual_flags)
                    for fragment in operations_expectation.flag_substrings
                ),
                actual=actual_flags,
                expected=list(operations_expectation.flag_substrings),
                detail="Expected operations flag phrases should appear in the summary.",
            )
        _append_check(
            checks,
            name="operations_checklist_updates",
            passed=len(operations_summary.get("checklist_updates", []))
            >= operations_expectation.min_checklist_updates,
            actual=len(operations_summary.get("checklist_updates", [])),
            expected=f">= {operations_expectation.min_checklist_updates}",
            detail="Operations engine should auto-satisfy the expected minimum checklist items.",
        )
    if scenario.cyber_summary_expectation is not None and cyber_summary is not None:
        cyber_expectation = scenario.cyber_summary_expectation
        control_status_map = {
            item["control_key"]: item["status"] for item in cyber_summary["controls"]
        }
        if cyber_expectation.required_statuses:
            _append_check(
                checks,
                name="cyber_statuses",
                passed=all(
                    control_status_map.get(control_key) == status
                    for control_key, status in cyber_expectation.required_statuses.items()
                ),
                actual=control_status_map,
                expected=cyber_expectation.required_statuses,
                detail="Cyber control statuses should match the expected control matrix.",
            )
        if cyber_expectation.required_certifications:
            _append_check(
                checks,
                name="cyber_certifications",
                passed=set(cyber_expectation.required_certifications).issubset(
                    cyber_summary["certifications"]
                ),
                actual=cyber_summary["certifications"],
                expected=list(cyber_expectation.required_certifications),
                detail="Expected cyber certifications should appear in the summary.",
            )
        _append_check(
            checks,
            name="cyber_breach_history",
            passed=len(cyber_summary["breach_history"]) >= cyber_expectation.min_breach_history,
            actual=len(cyber_summary["breach_history"]),
            expected=f">= {cyber_expectation.min_breach_history}",
            detail="Cyber summary should surface the expected breach-history volume.",
        )
        if cyber_expectation.flag_substrings:
            actual_flags = cyber_summary["flags"]
            _append_check(
                checks,
                name="cyber_flags",
                passed=all(
                    any(fragment.lower() in flag.lower() for flag in actual_flags)
                    for fragment in cyber_expectation.flag_substrings
                ),
                actual=actual_flags,
                expected=list(cyber_expectation.flag_substrings),
                detail="Expected cyber flag phrases should appear in the summary.",
            )
        _append_check(
            checks,
            name="cyber_checklist_updates",
            passed=len(cyber_summary.get("checklist_updates", []))
            >= cyber_expectation.min_checklist_updates,
            actual=len(cyber_summary.get("checklist_updates", [])),
            expected=f">= {cyber_expectation.min_checklist_updates}",
            detail="Cyber engine should auto-satisfy the expected minimum checklist items.",
        )
    if scenario.forensic_summary_expectation is not None and forensic_flags is not None:
        forensic_expectation = scenario.forensic_summary_expectation
        actual_flag_types = sorted(flag["flag_type"] for flag in forensic_flags)
        _append_check(
            checks,
            name="forensic_flag_count",
            passed=len(forensic_flags) >= forensic_expectation.min_flag_count,
            actual=len(forensic_flags),
            expected=f">= {forensic_expectation.min_flag_count}",
            detail="Forensic endpoint should return the expected minimum flag count.",
        )
        if forensic_expectation.required_flag_types:
            _append_check(
                checks,
                name="forensic_flag_types",
                passed=set(forensic_expectation.required_flag_types).issubset(actual_flag_types),
                actual=actual_flag_types,
                expected=list(forensic_expectation.required_flag_types),
                detail="Expected forensic flag types should appear in the endpoint response.",
            )
    if scenario.buy_side_analysis_expectation is not None and buy_side_analysis is not None:
        buy_side_expectation = scenario.buy_side_analysis_expectation
        _append_check(
            checks,
            name="buy_side_valuation_bridge_count",
            passed=len(buy_side_analysis["valuation_bridge"])
            >= buy_side_expectation.min_valuation_bridge_items,
            actual=len(buy_side_analysis["valuation_bridge"]),
            expected=f">= {buy_side_expectation.min_valuation_bridge_items}",
            detail="Buy-side analysis should produce the expected valuation bridge depth.",
        )
        _append_check(
            checks,
            name="buy_side_spa_issue_count",
            passed=len(buy_side_analysis["spa_issues"]) >= buy_side_expectation.min_spa_issue_count,
            actual=len(buy_side_analysis["spa_issues"]),
            expected=f">= {buy_side_expectation.min_spa_issue_count}",
            detail="Buy-side analysis should produce the expected SPA issue depth.",
        )
        _append_check(
            checks,
            name="buy_side_pmi_risk_count",
            passed=len(buy_side_analysis["pmi_risks"]) >= buy_side_expectation.min_pmi_risk_count,
            actual=len(buy_side_analysis["pmi_risks"]),
            expected=f">= {buy_side_expectation.min_pmi_risk_count}",
            detail="Buy-side analysis should produce the expected PMI risk depth.",
        )
        if buy_side_expectation.flag_substrings:
            _append_check(
                checks,
                name="buy_side_flags",
                passed=all(
                    any(fragment.lower() in flag.lower() for flag in buy_side_analysis["flags"])
                    for fragment in buy_side_expectation.flag_substrings
                ),
                actual=buy_side_analysis["flags"],
                expected=list(buy_side_expectation.flag_substrings),
                detail="Expected buy-side flag phrases should appear in the summary.",
            )
        _append_check(
            checks,
            name="buy_side_checklist_updates",
            passed=len(buy_side_analysis.get("checklist_updates", []))
            >= buy_side_expectation.min_checklist_updates,
            actual=len(buy_side_analysis.get("checklist_updates", [])),
            expected=f">= {buy_side_expectation.min_checklist_updates}",
            detail="Buy-side engine should auto-satisfy the expected minimum checklist items.",
        )
    if scenario.borrower_scorecard_expectation is not None and borrower_scorecard is not None:
        borrower_expectation = scenario.borrower_scorecard_expectation
        _append_check(
            checks,
            name="borrower_overall_score",
            passed=borrower_scorecard["overall_score"] >= borrower_expectation.min_overall_score,
            actual=borrower_scorecard["overall_score"],
            expected=f">= {borrower_expectation.min_overall_score}",
            detail="Borrower scorecard should produce the expected overall score floor.",
        )
        if borrower_expectation.expected_rating is not None:
            _append_check(
                checks,
                name="borrower_rating",
                passed=borrower_scorecard["overall_rating"] == borrower_expectation.expected_rating,
                actual=borrower_scorecard["overall_rating"],
                expected=borrower_expectation.expected_rating,
                detail="Borrower scorecard rating should match the expected motion-pack outcome.",
            )
        _append_check(
            checks,
            name="borrower_financial_health_score",
            passed=borrower_scorecard["financial_health"]["score"]
            >= borrower_expectation.min_financial_health_score,
            actual=borrower_scorecard["financial_health"]["score"],
            expected=f">= {borrower_expectation.min_financial_health_score}",
            detail="Financial-health scoring should meet the expected floor.",
        )
        _append_check(
            checks,
            name="borrower_collateral_score",
            passed=borrower_scorecard["collateral"]["score"]
            >= borrower_expectation.min_collateral_score,
            actual=borrower_scorecard["collateral"]["score"],
            expected=f">= {borrower_expectation.min_collateral_score}",
            detail="Collateral scoring should meet the expected floor.",
        )
        _append_check(
            checks,
            name="borrower_covenant_score",
            passed=borrower_scorecard["covenants"]["score"]
            >= borrower_expectation.min_covenant_score,
            actual=borrower_scorecard["covenants"]["score"],
            expected=f">= {borrower_expectation.min_covenant_score}",
            detail="Covenant scoring should meet the expected floor.",
        )
        _append_check(
            checks,
            name="borrower_covenant_items",
            passed=len(borrower_scorecard["covenant_tracking"])
            >= borrower_expectation.min_covenant_items,
            actual=len(borrower_scorecard["covenant_tracking"]),
            expected=f">= {borrower_expectation.min_covenant_items}",
            detail="Borrower scorecard should expose the expected covenant-tracking depth.",
        )
        _append_check(
            checks,
            name="borrower_checklist_updates",
            passed=len(borrower_scorecard.get("checklist_updates", []))
            >= borrower_expectation.min_checklist_updates,
            actual=len(borrower_scorecard.get("checklist_updates", [])),
            expected=f">= {borrower_expectation.min_checklist_updates}",
            detail="Credit engine should auto-satisfy the expected minimum checklist items.",
        )
    if scenario.vendor_risk_tier_expectation is not None and vendor_risk_tier is not None:
        vendor_expectation = scenario.vendor_risk_tier_expectation
        _append_check(
            checks,
            name="vendor_overall_score",
            passed=vendor_risk_tier["overall_score"] >= vendor_expectation.min_overall_score,
            actual=vendor_risk_tier["overall_score"],
            expected=f">= {vendor_expectation.min_overall_score}",
            detail="Vendor tiering should produce the expected overall score floor.",
        )
        if vendor_expectation.expected_tier is not None:
            _append_check(
                checks,
                name="vendor_expected_tier",
                passed=vendor_risk_tier["tier"] == vendor_expectation.expected_tier,
                actual=vendor_risk_tier["tier"],
                expected=vendor_expectation.expected_tier,
                detail="Vendor tier should match the expected motion-pack outcome.",
            )
        if vendor_expectation.required_factors:
            actual_factors = sorted(
                item["factor"] for item in vendor_risk_tier["scoring_breakdown"]
            )
            _append_check(
                checks,
                name="vendor_required_factors",
                passed=set(vendor_expectation.required_factors).issubset(actual_factors),
                actual=actual_factors,
                expected=list(vendor_expectation.required_factors),
                detail="Vendor score breakdown should include the expected factors.",
            )
        _append_check(
            checks,
            name="vendor_questionnaire_items",
            passed=len(vendor_risk_tier["questionnaire"])
            >= vendor_expectation.min_questionnaire_items,
            actual=len(vendor_risk_tier["questionnaire"]),
            expected=f">= {vendor_expectation.min_questionnaire_items}",
            detail="Vendor questionnaire should include the expected section depth.",
        )
        if vendor_expectation.required_certifications:
            _append_check(
                checks,
                name="vendor_required_certifications",
                passed=set(vendor_expectation.required_certifications).issubset(
                    vendor_risk_tier["certifications_required"]
                ),
                actual=vendor_risk_tier["certifications_required"],
                expected=list(vendor_expectation.required_certifications),
                detail="Vendor tiering should request the expected certification set.",
            )
        if vendor_expectation.flag_substrings:
            _append_check(
                checks,
                name="vendor_flags",
                passed=all(
                    any(fragment.lower() in flag.lower() for flag in vendor_risk_tier["flags"])
                    for fragment in vendor_expectation.flag_substrings
                ),
                actual=vendor_risk_tier["flags"],
                expected=list(vendor_expectation.flag_substrings),
                detail="Expected vendor flag phrases should appear in the summary.",
            )
        _append_check(
            checks,
            name="vendor_checklist_updates",
            passed=len(vendor_risk_tier.get("checklist_updates", []))
            >= vendor_expectation.min_checklist_updates,
            actual=len(vendor_risk_tier.get("checklist_updates", [])),
            expected=f">= {vendor_expectation.min_checklist_updates}",
            detail="Vendor engine should auto-satisfy the expected minimum checklist items.",
        )
    if scenario.tech_saas_metrics_expectation is not None and tech_saas_metrics is not None:
        tech_expectation = scenario.tech_saas_metrics_expectation
        if tech_expectation.expected_arr is not None:
            actual_arr = tech_saas_metrics["arr"]
            _append_check(
                checks,
                name="tech_saas_arr",
                passed=actual_arr is not None
                and abs(actual_arr - tech_expectation.expected_arr) < 0.0001,
                actual=actual_arr,
                expected=tech_expectation.expected_arr,
                detail="Tech/SaaS ARR should match the expected sector extraction.",
            )
        if tech_expectation.expected_mrr is not None:
            actual_mrr = tech_saas_metrics["mrr"]
            _append_check(
                checks,
                name="tech_saas_mrr",
                passed=actual_mrr is not None
                and abs(actual_mrr - tech_expectation.expected_mrr) < 0.0001,
                actual=actual_mrr,
                expected=tech_expectation.expected_mrr,
                detail="Tech/SaaS MRR should match the expected sector extraction.",
            )
        if tech_expectation.expected_nrr is not None:
            actual_nrr = tech_saas_metrics["nrr"]
            _append_check(
                checks,
                name="tech_saas_nrr",
                passed=actual_nrr is not None
                and abs(actual_nrr - tech_expectation.expected_nrr) < 0.0001,
                actual=actual_nrr,
                expected=tech_expectation.expected_nrr,
                detail="Tech/SaaS NRR should match the expected sector extraction.",
            )
        if tech_expectation.expected_churn is not None:
            actual_churn = tech_saas_metrics["churn_rate"]
            _append_check(
                checks,
                name="tech_saas_churn",
                passed=actual_churn is not None
                and abs(actual_churn - tech_expectation.expected_churn) < 0.0001,
                actual=actual_churn,
                expected=tech_expectation.expected_churn,
                detail="Tech/SaaS churn should match the expected sector extraction.",
            )
        if tech_expectation.expected_payback_months is not None:
            actual_payback = tech_saas_metrics["payback_months"]
            _append_check(
                checks,
                name="tech_saas_payback",
                passed=actual_payback is not None
                and abs(actual_payback - tech_expectation.expected_payback_months) < 0.0001,
                actual=actual_payback,
                expected=tech_expectation.expected_payback_months,
                detail="Tech/SaaS payback should match the expected sector extraction.",
            )
        _append_check(
            checks,
            name="tech_saas_arr_waterfall_count",
            passed=len(tech_saas_metrics["arr_waterfall"])
            >= tech_expectation.min_arr_waterfall_items,
            actual=len(tech_saas_metrics["arr_waterfall"]),
            expected=f">= {tech_expectation.min_arr_waterfall_items}",
            detail="Tech/SaaS engine should expose the expected ARR waterfall depth.",
        )
        if tech_expectation.flag_substrings:
            _append_check(
                checks,
                name="tech_saas_flags",
                passed=all(
                    any(fragment.lower() in flag.lower() for flag in tech_saas_metrics["flags"])
                    for fragment in tech_expectation.flag_substrings
                ),
                actual=tech_saas_metrics["flags"],
                expected=list(tech_expectation.flag_substrings),
                detail="Expected Tech/SaaS flag phrases should appear in the sector summary.",
            )
        _append_check(
            checks,
            name="tech_saas_checklist_updates",
            passed=len(tech_saas_metrics.get("checklist_updates", []))
            >= tech_expectation.min_checklist_updates,
            actual=len(tech_saas_metrics.get("checklist_updates", [])),
            expected=f">= {tech_expectation.min_checklist_updates}",
            detail="Tech/SaaS engine should auto-satisfy the expected minimum checklist items.",
        )
    if scenario.manufacturing_metrics_expectation is not None and manufacturing_metrics is not None:
        manufacturing_expectation = scenario.manufacturing_metrics_expectation
        for name, actual, expected, detail in (
            (
                "manufacturing_capacity_utilization",
                manufacturing_metrics["capacity_utilization"],
                manufacturing_expectation.expected_capacity_utilization,
                "Manufacturing capacity utilization should match the expected sector extraction.",
            ),
            (
                "manufacturing_dio",
                manufacturing_metrics["dio"],
                manufacturing_expectation.expected_dio,
                "Manufacturing DIO should match the expected sector extraction.",
            ),
            (
                "manufacturing_dso",
                manufacturing_metrics["dso"],
                manufacturing_expectation.expected_dso,
                "Manufacturing DSO should match the expected sector extraction.",
            ),
            (
                "manufacturing_dpo",
                manufacturing_metrics["dpo"],
                manufacturing_expectation.expected_dpo,
                "Manufacturing DPO should match the expected sector extraction.",
            ),
            (
                "manufacturing_asset_turnover",
                manufacturing_metrics["asset_turnover"],
                manufacturing_expectation.expected_asset_turnover,
                "Manufacturing asset turnover should match the expected sector extraction.",
            ),
        ):
            if expected is None:
                continue
            _append_check(
                checks,
                name=name,
                passed=actual is not None and abs(actual - expected) < 0.0001,
                actual=actual,
                expected=expected,
                detail=detail,
            )
        _append_check(
            checks,
            name="manufacturing_asset_register_count",
            passed=len(manufacturing_metrics["asset_register"])
            >= manufacturing_expectation.min_asset_register_items,
            actual=len(manufacturing_metrics["asset_register"]),
            expected=f">= {manufacturing_expectation.min_asset_register_items}",
            detail="Manufacturing engine should expose the expected asset-register depth.",
        )
        if manufacturing_expectation.flag_substrings:
            _append_check(
                checks,
                name="manufacturing_flags",
                passed=all(
                    any(fragment.lower() in flag.lower() for flag in manufacturing_metrics["flags"])
                    for fragment in manufacturing_expectation.flag_substrings
                ),
                actual=manufacturing_metrics["flags"],
                expected=list(manufacturing_expectation.flag_substrings),
                detail="Expected manufacturing flag phrases should appear in the sector summary.",
            )
        _append_check(
            checks,
            name="manufacturing_checklist_updates",
            passed=len(manufacturing_metrics.get("checklist_updates", []))
            >= manufacturing_expectation.min_checklist_updates,
            actual=len(manufacturing_metrics.get("checklist_updates", [])),
            expected=f">= {manufacturing_expectation.min_checklist_updates}",
            detail="Manufacturing engine should auto-satisfy the expected minimum checklist items.",
        )
    if scenario.bfsi_nbfc_metrics_expectation is not None and bfsi_nbfc_metrics is not None:
        bfsi_expectation = scenario.bfsi_nbfc_metrics_expectation
        for name, actual, expected, detail in (
            (
                "bfsi_gnpa",
                bfsi_nbfc_metrics["gnpa"],
                bfsi_expectation.expected_gnpa,
                "BFSI GNPA should match the expected sector extraction.",
            ),
            (
                "bfsi_nnpa",
                bfsi_nbfc_metrics["nnpa"],
                bfsi_expectation.expected_nnpa,
                "BFSI NNPA should match the expected sector extraction.",
            ),
            (
                "bfsi_crar",
                bfsi_nbfc_metrics["crar"],
                bfsi_expectation.expected_crar,
                "BFSI CRAR should match the expected sector extraction.",
            ),
            (
                "bfsi_alm_mismatch",
                bfsi_nbfc_metrics["alm_mismatch"],
                bfsi_expectation.expected_alm_mismatch,
                "BFSI ALM mismatch should match the expected sector extraction.",
            ),
        ):
            if expected is None:
                continue
            _append_check(
                checks,
                name=name,
                passed=actual is not None and abs(actual - expected) < 0.0001,
                actual=actual,
                expected=expected,
                detail=detail,
            )
        if bfsi_expectation.expected_psl_status is not None:
            _append_check(
                checks,
                name="bfsi_psl_status",
                passed=bfsi_nbfc_metrics["psl_compliance"] == bfsi_expectation.expected_psl_status,
                actual=bfsi_nbfc_metrics["psl_compliance"],
                expected=bfsi_expectation.expected_psl_status,
                detail="BFSI PSL status should match the expected sector extraction.",
            )
        _append_check(
            checks,
            name="bfsi_alm_bucket_gaps",
            passed=len(bfsi_nbfc_metrics["alm_bucket_gaps"])
            >= bfsi_expectation.min_alm_bucket_gaps,
            actual=len(bfsi_nbfc_metrics["alm_bucket_gaps"]),
            expected=f">= {bfsi_expectation.min_alm_bucket_gaps}",
            detail="BFSI engine should expose the expected ALM bucket depth.",
        )
        if bfsi_expectation.flag_substrings:
            _append_check(
                checks,
                name="bfsi_flags",
                passed=all(
                    any(fragment.lower() in flag.lower() for flag in bfsi_nbfc_metrics["flags"])
                    for fragment in bfsi_expectation.flag_substrings
                ),
                actual=bfsi_nbfc_metrics["flags"],
                expected=list(bfsi_expectation.flag_substrings),
                detail="Expected BFSI flag phrases should appear in the sector summary.",
            )
        _append_check(
            checks,
            name="bfsi_checklist_updates",
            passed=len(bfsi_nbfc_metrics.get("checklist_updates", []))
            >= bfsi_expectation.min_checklist_updates,
            actual=len(bfsi_nbfc_metrics.get("checklist_updates", [])),
            expected=f">= {bfsi_expectation.min_checklist_updates}",
            detail="BFSI engine should auto-satisfy the expected minimum checklist items.",
        )

    return {
        "code": scenario.code,
        "name": scenario.name,
        "description": scenario.description,
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "metrics": metrics,
        "issue_scan": {
            "first": issue_scan_first,
            "second": issue_scan_second,
        },
        "financial_summary": financial_summary,
        "legal_summary": legal_summary,
        "tax_summary": tax_summary,
        "compliance_matrix": compliance_matrix,
        "commercial_summary": commercial_summary,
        "operations_summary": operations_summary,
        "cyber_summary": cyber_summary,
        "forensic_flags": forensic_flags,
        "buy_side_analysis": buy_side_analysis,
        "borrower_scorecard": borrower_scorecard,
        "vendor_risk_tier": vendor_risk_tier,
        "tech_saas_metrics": tech_saas_metrics,
        "manufacturing_metrics": manufacturing_metrics,
        "bfsi_nbfc_metrics": bfsi_nbfc_metrics,
        "scenario": {
            "case_payload": scenario.case_payload,
            "satisfy_all_checklist_items": scenario.satisfy_all_checklist_items,
            "scan_issues": scenario.scan_issues,
            "checklist_updates": [asdict(item) for item in scenario.checklist_updates],
        },
    }


def _aggregate_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total_documents": sum(result["metrics"].get("document_count", 0) for result in results),
        "total_evidence": sum(result["metrics"].get("evidence_count", 0) for result in results),
        "total_issues": sum(result["metrics"].get("issue_count", 0) for result in results),
        "average_trace_event_count": (
            sum(result["metrics"].get("trace_event_count", 0) for result in results) / len(results)
            if results
            else 0
        ),
        "average_report_bundle_count": (
            sum(result["metrics"].get("report_bundle_count", 0) for result in results)
            / len(results)
            if results
            else 0
        ),
    }


def _run_suite_definition(suite: EvaluationSuiteDefinition) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for scenario in suite.scenarios:
        try:
            results.append(_evaluate_scenario(scenario))
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "code": scenario.code,
                    "name": scenario.name,
                    "description": scenario.description,
                    "passed": False,
                    "checks": [
                        {
                            "name": "scenario_execution",
                            "passed": False,
                            "actual": str(exc),
                            "expected": "successful end-to-end execution",
                            "detail": "The evaluation scenario raised an exception.",
                        }
                    ],
                    "metrics": {},
                    "issue_scan": {"first": None, "second": None},
                    "scenario": {
                        "case_payload": scenario.case_payload,
                        "satisfy_all_checklist_items": scenario.satisfy_all_checklist_items,
                        "scan_issues": scenario.scan_issues,
                        "checklist_updates": [asdict(item) for item in scenario.checklist_updates],
                    },
                }
            )

    passed_count = sum(1 for result in results if result["passed"])
    return {
        "suite": suite.key,
        "title": suite.title,
        "generated_at": datetime.now(UTC).isoformat(),
        "scenario_count": len(results),
        "passed_count": passed_count,
        "failed_count": len(results) - passed_count,
        "success_rate": round((passed_count / len(results)) if results else 0.0, 4),
        "bundle_kinds_required": sorted(DEFAULT_BUNDLE_KINDS),
        "aggregate_metrics": _aggregate_metrics(results),
        "scenarios": results,
    }


def _write_report(
    output_root: Path,
    artifact_prefix: str,
    report: dict[str, Any],
) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = output_root / f"{artifact_prefix}-{timestamp}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path


def run_evaluation_suite(
    output_dir: Path | None = None,
    suite_key: str = "all",
) -> tuple[Path, dict[str, Any]]:
    output_root = (output_dir or DEFAULT_OUTPUT_DIR).resolve()

    if suite_key != "all":
        suite = EVALUATION_SUITES[suite_key]
        report = _run_suite_definition(suite)
        return _write_report(output_root, suite.artifact_prefix, report), report

    suite_reports: list[dict[str, Any]] = []
    for suite in EVALUATION_SUITES.values():
        suite_reports.append(_run_suite_definition(suite))

    total_scenarios = sum(report["scenario_count"] for report in suite_reports)
    passed_scenarios = sum(report["passed_count"] for report in suite_reports)
    combined_report = {
        "suite": "all_supported_suites",
        "generated_at": datetime.now(UTC).isoformat(),
        "suite_count": len(suite_reports),
        "scenario_count": total_scenarios,
        "passed_count": passed_scenarios,
        "failed_count": total_scenarios - passed_scenarios,
        "success_rate": round((passed_scenarios / total_scenarios) if total_scenarios else 0.0, 4),
        "suites": suite_reports,
    }
    return _write_report(output_root, "all-supported-suites", combined_report), combined_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the evaluation suites for the CrewAI Enterprise Pipeline."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where evaluation JSON artifacts should be written.",
    )
    parser.add_argument(
        "--suite",
        choices=["all", *EVALUATION_SUITES.keys()],
        default="all",
        help="Run a specific evaluation suite or all supported suites.",
    )
    args = parser.parse_args()

    report_path, report = run_evaluation_suite(args.output_dir, suite_key=args.suite)
    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "suite": report["suite"],
                "scenario_count": report["scenario_count"],
                "passed_count": report["passed_count"],
                "failed_count": report["failed_count"],
                "success_rate": report["success_rate"],
            },
            indent=2,
        )
    )
    if report["failed_count"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
