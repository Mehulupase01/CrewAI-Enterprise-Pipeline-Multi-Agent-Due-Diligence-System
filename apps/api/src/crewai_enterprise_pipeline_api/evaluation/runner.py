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
    PHASE5_FIRST_SLICE_SCENARIOS,
    ChecklistUpdateFixture,
    EvaluationScenario,
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
        raise RuntimeError(
            f"{step} failed with status {response.status_code}: {response.text}"
        )
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
                "note": "Satisfied by the automated first-slice evaluation harness.",
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
                            upload.content.encode("utf-8"),
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
        detail="Executive memo status should reflect approval readiness.",
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
        detail="The first-slice workstream syntheses should be persisted.",
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
        "scenario": {
            "case_payload": scenario.case_payload,
            "satisfy_all_checklist_items": scenario.satisfy_all_checklist_items,
            "scan_issues": scenario.scan_issues,
            "checklist_updates": [asdict(item) for item in scenario.checklist_updates],
        },
    }


def run_evaluation_suite(output_dir: Path | None = None) -> tuple[Path, dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for scenario in PHASE5_FIRST_SLICE_SCENARIOS:
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
    aggregate_metrics = {
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

    report = {
        "suite": "phase5_first_slice_evaluation",
        "generated_at": datetime.now(UTC).isoformat(),
        "scenario_count": len(results),
        "passed_count": passed_count,
        "failed_count": len(results) - passed_count,
        "success_rate": round((passed_count / len(results)) if results else 0.0, 4),
        "bundle_kinds_required": sorted(DEFAULT_BUNDLE_KINDS),
        "aggregate_metrics": aggregate_metrics,
        "scenarios": results,
    }

    output_root = (output_dir or DEFAULT_OUTPUT_DIR).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = output_root / f"phase5-first-slice-{timestamp}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path, report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the first-slice evaluation suite for the CrewAI Enterprise Pipeline."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where the evaluation JSON artifact should be written.",
    )
    args = parser.parse_args()

    report_path, report = run_evaluation_suite(args.output_dir)
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
