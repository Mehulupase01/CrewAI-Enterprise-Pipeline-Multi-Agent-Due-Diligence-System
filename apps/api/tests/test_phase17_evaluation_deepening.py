from __future__ import annotations

import json
from pathlib import Path


def test_phase17_live_validation_skips_when_not_configured(monkeypatch, tmp_path: Path) -> None:
    from crewai_enterprise_pipeline_api.core.settings import get_settings
    from crewai_enterprise_pipeline_api.evaluation.live_validation import (
        run_connector_validation_suite,
        run_openrouter_benchmark_suite,
    )

    monkeypatch.delenv("LLM_API_KEY", raising=False)
    get_settings.cache_clear()

    try:
        _, openrouter_report = run_openrouter_benchmark_suite(tmp_path, require_live=False)
        _, connector_report = run_connector_validation_suite(tmp_path, require_live=False)
    finally:
        get_settings.cache_clear()

    assert openrouter_report["failed_count"] == 0
    assert openrouter_report["skipped_count"] == 1
    assert connector_report["failed_count"] == 0
    assert connector_report["skipped_count"] >= 1


def test_phase17_regression_compare_detects_score_drop() -> None:
    from crewai_enterprise_pipeline_api.evaluation.regression import compare_report_to_baseline

    baseline = {
        "generated_at": "2026-04-01T00:00:00Z",
        "suite": "all_supported_suites",
        "max_drop_fraction": 0.05,
        "success_rate": 1.0,
        "overall_score": 0.9,
        "suite_scores": {
            "phase17_evaluation_deepening": {"success_rate": 1.0, "overall_score": 0.9}
        },
    }
    report = {
        "suite": "all_supported_suites",
        "success_rate": 0.93,
        "quality_summary": {"average": {"overall_score": 0.82}},
        "suites": [
            {
                "suite": "phase17_evaluation_deepening",
                "success_rate": 0.92,
                "quality_summary": {"average": {"overall_score": 0.81}},
            }
        ],
    }

    comparison = compare_report_to_baseline(report=report, baseline=baseline)

    assert comparison["passed"] is False
    failing_checks = [check["name"] for check in comparison["checks"] if not check["passed"]]
    assert "overall_score_regression" in failing_checks
    assert "phase17_evaluation_deepening_overall_score" in failing_checks


def test_phase17_load_benchmark_runs_at_low_volume(tmp_path: Path) -> None:
    from crewai_enterprise_pipeline_api.evaluation.performance import run_load_benchmark

    _, report = run_load_benchmark(tmp_path, total_requests=6, concurrency=2)

    assert report["suite"] == "phase17_load_benchmark"
    assert report["checks"]
    assert "system_health" in report["benchmarks"]
    assert "issues_scan" in report["benchmarks"]
    assert "search" in report["benchmarks"]


def test_phase17_quality_scorecard_and_baseline_round_trip(tmp_path: Path) -> None:
    from crewai_enterprise_pipeline_api.evaluation.regression import (
        build_baseline_from_report,
        compare_report_to_baseline,
    )
    from crewai_enterprise_pipeline_api.evaluation.runner import run_evaluation_suite

    report_path, report = run_evaluation_suite(tmp_path, suite_key="phase17_evaluation_deepening")
    assert report["scenario_count"] >= 8
    assert report["quality_summary"]["average"]["overall_score"] >= 0.8
    assert report["quality_summary"]["minimum_overall_score"] >= 0.8
    assert all("quality_scorecard" in scenario for scenario in report["scenarios"])

    baseline = build_baseline_from_report(report, max_drop_fraction=0.05)
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")

    comparison = compare_report_to_baseline(
        report=report,
        baseline=json.loads(baseline_path.read_text(encoding="utf-8")),
    )
    assert comparison["passed"] is True
    assert report_path.exists()
