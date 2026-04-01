from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any

import httpx

from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.db.session import close_database
from crewai_enterprise_pipeline_api.evaluation.runner import DEFAULT_OUTPUT_DIR

ENV_KEYS = (
    "DATABASE_URL",
    "APP_ENV",
    "AUTO_CREATE_SCHEMA",
    "STORAGE_BACKEND",
    "LOCAL_STORAGE_ROOT",
    "RATE_LIMIT_ENABLED",
)


def _write_report(output_root: Path, artifact_prefix: str, report: dict[str, Any]) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = output_root / f"{artifact_prefix}-{timestamp}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path


@contextmanager
def _isolated_runtime_root(runtime_root: Path):
    previous_env = {key: os.environ.get(key) for key in ENV_KEYS}
    runtime_root.mkdir(parents=True, exist_ok=True)
    storage_root = runtime_root / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)

    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(runtime_root / 'perf.db').as_posix()}"
    os.environ["APP_ENV"] = "test"
    os.environ["AUTO_CREATE_SCHEMA"] = "true"
    os.environ["STORAGE_BACKEND"] = "local"
    os.environ["LOCAL_STORAGE_ROOT"] = str(storage_root.resolve())
    os.environ["RATE_LIMIT_ENABLED"] = "false"
    get_settings.cache_clear()

    try:
        yield
    finally:
        get_settings.cache_clear()
        asyncio.run(close_database())
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return round(ordered[index], 2)


async def _seed_case(client: httpx.AsyncClient) -> str:
    case_response = await client.post(
        "/api/v1/cases",
        json={
            "name": "Phase 17 Performance Case",
            "target_name": "Performance Systems Private Limited",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    case_response.raise_for_status()
    case_id = case_response.json()["id"]

    seed_response = await client.post(f"/api/v1/cases/{case_id}/checklist/seed")
    seed_response.raise_for_status()

    upload_response = await client.post(
        f"/api/v1/cases/{case_id}/documents/upload",
        data={
            "document_kind": "audited_financials",
            "source_kind": "uploaded_dataroom",
            "workstream_domain": "financial_qoe",
            "title": "Performance financial note",
            "evidence_kind": "metric",
        },
        files={
            "file": (
                "performance_finance.txt",
                (
                    b"Revenue grew 29 percent year over year. "
                    b"EBITDA margin improved to 17 percent. "
                    b"Cash conversion weakened after receivables stretched beyond 75 days."
                ),
                "text/plain",
            )
        },
    )
    upload_response.raise_for_status()

    evidence_response = await client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={
            "title": "Performance issue signal",
            "evidence_kind": "risk",
            "workstream_domain": "tax",
            "citation": "Performance tax note",
            "excerpt": "A GST notice was issued and remains under response.",
            "confidence": 0.82,
        },
    )
    evidence_response.raise_for_status()
    return case_id


async def _run_request_benchmark(
    client: httpx.AsyncClient,
    *,
    method: str,
    path: str | None = None,
    paths: list[str] | None = None,
    total_requests: int,
    concurrency: int,
    json_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if path is None and not paths:
        raise ValueError("Either path or paths must be provided.")
    semaphore = asyncio.Semaphore(concurrency)
    durations: list[float] = []
    errors: list[str] = []

    resolved_paths = paths or [path] * total_requests
    if len(resolved_paths) < total_requests:
        raise ValueError("Not enough request paths were provided for the benchmark.")

    async def _single_request(request_path: str) -> None:
        async with semaphore:
            started_at = perf_counter()
            response = await client.request(method, request_path, json=json_payload)
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            durations.append(duration_ms)
            if response.status_code >= 400:
                errors.append(f"{request_path} -> {response.status_code}: {response.text}")

    await asyncio.gather(
        *[
            _single_request(request_path)
            for request_path in resolved_paths[:total_requests]
        ]
    )
    return {
        "request_count": total_requests,
        "concurrency": concurrency,
        "error_count": len(errors),
        "p50_ms": _percentile(durations, 0.50),
        "p95_ms": _percentile(durations, 0.95),
        "max_ms": round(max(durations) if durations else 0.0, 2),
        "errors": errors[:5],
    }


async def _build_performance_report(
    *,
    total_requests: int,
    concurrency: int,
) -> dict[str, Any]:
    from crewai_enterprise_pipeline_api.main import create_app

    app = create_app()
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            case_id = await _seed_case(client)
            issue_scan_request_count = max(10, total_requests // 2)
            issue_scan_paths = [
                f"/api/v1/cases/{await _seed_case(client)}/issues/scan"
                for _ in range(issue_scan_request_count)
            ]
            health = await _run_request_benchmark(
                client,
                method="GET",
                path="/api/v1/system/health",
                total_requests=total_requests,
                concurrency=concurrency,
            )
            issue_scan = await _run_request_benchmark(
                client,
                method="POST",
                paths=issue_scan_paths,
                total_requests=issue_scan_request_count,
                concurrency=max(5, concurrency // 2),
            )
            search = await _run_request_benchmark(
                client,
                method="POST",
                path=f"/api/v1/cases/{case_id}/search",
                total_requests=max(10, total_requests // 2),
                concurrency=max(5, concurrency // 2),
                json_payload={"query": "revenue", "top_k": 5},
            )

    thresholds = {
        "system_health": 500.0,
        "issues_scan": 2000.0,
        "search": 5000.0,
    }
    checks = [
        {
            "name": "system_health_p95",
            "passed": health["p95_ms"] < thresholds["system_health"] and health["error_count"] == 0,
            "actual": health["p95_ms"],
            "expected": f"< {thresholds['system_health']} ms and 0 errors",
        },
        {
            "name": "issues_scan_p95",
            "passed": (
                issue_scan["p95_ms"] < thresholds["issues_scan"]
                and issue_scan["error_count"] == 0
            ),
            "actual": issue_scan["p95_ms"],
            "expected": f"< {thresholds['issues_scan']} ms and 0 errors",
        },
        {
            "name": "search_p95",
            "passed": search["p95_ms"] < thresholds["search"] and search["error_count"] == 0,
            "actual": search["p95_ms"],
            "expected": f"< {thresholds['search']} ms and 0 errors",
        },
    ]
    return {
        "suite": "phase17_load_benchmark",
        "generated_at": datetime.now(UTC).isoformat(),
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "benchmarks": {
            "system_health": health,
            "issues_scan": issue_scan,
            "search": search,
        },
    }


def run_load_benchmark(
    output_dir: Path | None = None,
    *,
    total_requests: int = 50,
    concurrency: int = 10,
) -> tuple[Path, dict[str, Any]]:
    with TemporaryDirectory(prefix="phase17-load-") as temp_dir:
        with _isolated_runtime_root(Path(temp_dir)):
            report = asyncio.run(
                _build_performance_report(
                    total_requests=total_requests,
                    concurrency=concurrency,
                )
            )
    report_path = _write_report(output_dir or DEFAULT_OUTPUT_DIR, "phase17-load-benchmark", report)
    return report_path, report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Phase 17 performance benchmark.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where performance JSON artifacts should be written.",
    )
    parser.add_argument("--total-requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()

    report_path, report = run_load_benchmark(
        args.output_dir,
        total_requests=args.total_requests,
        concurrency=args.concurrency,
    )
    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "suite": report["suite"],
                "passed": report["passed"],
                "checks": report["checks"],
            },
            indent=2,
        )
    )
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
