from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx

from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.evaluation.runner import DEFAULT_OUTPUT_DIR
from crewai_enterprise_pipeline_api.source_adapters import get_registered_adapters

OPENROUTER_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
CONNECTOR_IDENTIFIER_ENV_MAP = {
    "mca21": "PHASE17_MCA21_IDENTIFIER",
    "gstin": "PHASE17_GSTIN_IDENTIFIER",
    "sebi_scores": "PHASE17_SEBI_SCORES_IDENTIFIER",
    "roc": "PHASE17_ROC_IDENTIFIER",
    "cibil": "PHASE17_CIBIL_IDENTIFIER",
    "sanctions": "PHASE17_SANCTIONS_IDENTIFIER",
}


def _write_report(output_root: Path, artifact_prefix: str, report: dict[str, Any]) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = output_root / f"{artifact_prefix}-{timestamp}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path


def _openrouter_text_tool_models(payload: dict[str, Any]) -> list[dict[str, Any]]:
    models: list[dict[str, Any]] = []
    for item in payload.get("data", []):
        output_modalities = item.get("architecture", {}).get("output_modalities") or ["text"]
        supports_text = "text" in output_modalities
        supported_parameters = set(item.get("supported_parameters") or [])
        supports_tools = "tools" in supported_parameters or "tool_choice" in supported_parameters
        if supports_text and supports_tools:
            models.append(item)
    return models


def run_openrouter_benchmark_suite(
    output_dir: Path | None = None,
    *,
    require_live: bool = False,
) -> tuple[Path, dict[str, Any]]:
    settings = get_settings()
    api_key = settings.llm_api_key
    base_url = settings.llm_base_url or OPENROUTER_DEFAULT_BASE_URL
    report: dict[str, Any] = {
        "suite": "phase17_openrouter_benchmark",
        "generated_at": datetime.now(UTC).isoformat(),
        "require_live": require_live,
        "passed_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "checks": [],
    }

    if not api_key:
        report["skipped_count"] = 1
        report["checks"].append(
            {
                "name": "openrouter_credentials",
                "status": "skipped" if not require_live else "failed",
                "detail": "LLM_API_KEY is not configured for live OpenRouter benchmarking.",
            }
        )
        if require_live:
            report["failed_count"] = 1
        return (
            _write_report(
                output_dir or DEFAULT_OUTPUT_DIR,
                "phase17-openrouter-benchmark",
                report,
            ),
            report,
        )

    selected_model = os.environ.get("PHASE17_OPENROUTER_MODEL")
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        with httpx.Client(timeout=30.0) as client:
            catalog_response = client.get(f"{base_url.rstrip('/')}/models", headers=headers)
            catalog_response.raise_for_status()
            catalog = catalog_response.json()
            models = _openrouter_text_tool_models(catalog)
            if not models:
                raise RuntimeError("No tool-capable text models were returned by OpenRouter.")
            if selected_model is None:
                selected_model = models[0]["id"]

            started_at = perf_counter()
            completion_response = client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={
                    **headers,
                    "Content-Type": "application/json",
                },
                json={
                    "model": selected_model,
                    "messages": [{"role": "user", "content": "Reply with the single word OK."}],
                    "temperature": 0,
                    "max_tokens": 8,
                },
            )
            completion_response.raise_for_status()
            completion_payload = completion_response.json()
            latency_ms = round((perf_counter() - started_at) * 1000, 2)
        content = (
            completion_payload.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        report["checks"].append(
            {
                "name": "openrouter_completion",
                "status": "passed",
                "selected_model": selected_model,
                "catalog_model_count": len(models),
                "latency_ms": latency_ms,
                "response_excerpt": content[:64],
                "detail": "OpenRouter catalog fetch and completion benchmark succeeded.",
            }
        )
        report["passed_count"] = 1
    except Exception as exc:  # noqa: BLE001
        report["checks"].append(
            {
                "name": "openrouter_completion",
                "status": "failed",
                "selected_model": selected_model,
                "detail": str(exc),
            }
        )
        report["failed_count"] = 1

    return (
        _write_report(
            output_dir or DEFAULT_OUTPUT_DIR,
            "phase17-openrouter-benchmark",
            report,
        ),
        report,
    )


async def _run_connector_live_validation(*, require_live: bool) -> dict[str, Any]:
    settings = get_settings()
    checks: list[dict[str, Any]] = []
    passed_count = 0
    failed_count = 0
    skipped_count = 0

    for adapter in get_registered_adapters():
        identifier_env = CONNECTOR_IDENTIFIER_ENV_MAP.get(adapter.adapter_id)
        identifier = os.environ.get(identifier_env or "")
        configured = adapter.is_live_configured(settings)
        if not configured or not identifier:
            status = "skipped"
            detail = "Adapter is not live-configured or has no identifier configured."
            if require_live:
                status = "failed"
                detail = (
                    "Live validation required but the adapter is missing live configuration "
                    "or a Phase 17 identifier environment variable."
                )
                failed_count += 1
            else:
                skipped_count += 1
            checks.append(
                {
                    "adapter_key": adapter.adapter_id,
                    "status": status,
                    "configured_live": configured,
                    "identifier_env": identifier_env,
                    "detail": detail,
                }
            )
            continue

        started_at = perf_counter()
        try:
            raw = await adapter.fetch_live(identifier, settings=settings)
            parsed_text = adapter.parse(raw)
            checks.append(
                {
                    "adapter_key": adapter.adapter_id,
                    "status": "passed",
                    "configured_live": True,
                    "identifier_env": identifier_env,
                    "latency_ms": round((perf_counter() - started_at) * 1000, 2),
                    "byte_count": len(raw.content),
                    "parsed_length": len(parsed_text),
                    "detail": "Live connector fetch and parse succeeded.",
                }
            )
            passed_count += 1
        except Exception as exc:  # noqa: BLE001
            checks.append(
                {
                    "adapter_key": adapter.adapter_id,
                    "status": "failed",
                    "configured_live": True,
                    "identifier_env": identifier_env,
                    "detail": str(exc),
                }
            )
            failed_count += 1

    return {
        "suite": "phase17_live_connector_validation",
        "generated_at": datetime.now(UTC).isoformat(),
        "require_live": require_live,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "checks": checks,
    }


def run_connector_validation_suite(
    output_dir: Path | None = None,
    *,
    require_live: bool = False,
) -> tuple[Path, dict[str, Any]]:
    report = asyncio.run(_run_connector_live_validation(require_live=require_live))
    return (
        _write_report(
            output_dir or DEFAULT_OUTPUT_DIR,
            "phase17-live-connectors",
            report,
        ),
        report,
    )


def run_live_validation_suites(
    output_dir: Path | None = None,
    *,
    suite: str = "all",
    require_live: bool = False,
) -> tuple[list[Path], dict[str, Any]]:
    reports: list[tuple[Path, dict[str, Any]]] = []
    if suite in {"all", "connectors"}:
        reports.append(run_connector_validation_suite(output_dir, require_live=require_live))
    if suite in {"all", "openrouter"}:
        reports.append(run_openrouter_benchmark_suite(output_dir, require_live=require_live))

    paths = [path for path, _ in reports]
    aggregate = {
        "suite": "phase17_live_validation",
        "generated_at": datetime.now(UTC).isoformat(),
        "require_live": require_live,
        "report_count": len(reports),
        "passed_count": sum(report["passed_count"] for _, report in reports),
        "failed_count": sum(report["failed_count"] for _, report in reports),
        "skipped_count": sum(report["skipped_count"] for _, report in reports),
        "reports": [report for _, report in reports],
    }
    return paths, aggregate


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 17 live validation suites.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where live-validation JSON artifacts should be written.",
    )
    parser.add_argument(
        "--suite",
        choices=["all", "connectors", "openrouter"],
        default="all",
        help="Run a specific live-validation suite or all supported suites.",
    )
    parser.add_argument(
        "--require-live",
        action="store_true",
        help="Fail when live credentials or identifiers are missing instead of skipping.",
    )
    args = parser.parse_args()

    report_paths, aggregate = run_live_validation_suites(
        args.output_dir,
        suite=args.suite,
        require_live=args.require_live,
    )
    print(
        json.dumps(
            {
                "report_paths": [str(path) for path in report_paths],
                "suite": aggregate["suite"],
                "report_count": aggregate["report_count"],
                "passed_count": aggregate["passed_count"],
                "failed_count": aggregate["failed_count"],
                "skipped_count": aggregate["skipped_count"],
            },
            indent=2,
        )
    )
    if aggregate["failed_count"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
