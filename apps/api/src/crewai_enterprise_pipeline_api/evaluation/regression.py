from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _latest_report(report_dir: Path) -> Path:
    candidates = sorted(
        report_dir.glob("all-supported-suites-*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"No all-supported-suites report found under {report_dir}.")
    return candidates[0]


def build_baseline_from_report(
    report: dict[str, Any],
    *,
    max_drop_fraction: float,
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "suite": report["suite"],
        "max_drop_fraction": max_drop_fraction,
        "scenario_count": report["scenario_count"],
        "success_rate": report["success_rate"],
        "overall_score": report.get("quality_summary", {})
        .get("average", {})
        .get("overall_score", 0.0),
        "suite_scores": {
            suite["suite"]: {
                "success_rate": suite["success_rate"],
                "overall_score": suite.get("quality_summary", {})
                .get("average", {})
                .get("overall_score", 0.0),
            }
            for suite in report.get("suites", [])
        },
    }


def compare_report_to_baseline(
    *,
    report: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    max_drop_fraction = float(baseline.get("max_drop_fraction", 0.05))
    checks: list[dict[str, Any]] = []

    overall_baseline = float(baseline.get("overall_score", 0.0))
    overall_actual = float(
        report.get("quality_summary", {}).get("average", {}).get("overall_score", 0.0)
    )
    overall_floor = round(overall_baseline * (1.0 - max_drop_fraction), 4)
    checks.append(
        {
            "name": "overall_score_regression",
            "passed": overall_actual >= overall_floor,
            "actual": overall_actual,
            "expected": f">= {overall_floor}",
        }
    )

    success_baseline = float(baseline.get("success_rate", 0.0))
    success_actual = float(report.get("success_rate", 0.0))
    success_floor = round(success_baseline * (1.0 - max_drop_fraction), 4)
    checks.append(
        {
            "name": "overall_success_rate_regression",
            "passed": success_actual >= success_floor,
            "actual": success_actual,
            "expected": f">= {success_floor}",
        }
    )

    current_suites = {suite["suite"]: suite for suite in report.get("suites", [])}
    for suite_key, suite_baseline in baseline.get("suite_scores", {}).items():
        current = current_suites.get(suite_key)
        if current is None:
            checks.append(
                {
                    "name": f"{suite_key}_presence",
                    "passed": False,
                    "actual": "missing",
                    "expected": "present",
                }
            )
            continue

        current_overall = float(
            current.get("quality_summary", {}).get("average", {}).get("overall_score", 0.0)
        )
        baseline_overall = float(suite_baseline.get("overall_score", 0.0))
        overall_floor = round(baseline_overall * (1.0 - max_drop_fraction), 4)
        checks.append(
            {
                "name": f"{suite_key}_overall_score",
                "passed": current_overall >= overall_floor,
                "actual": current_overall,
                "expected": f">= {overall_floor}",
            }
        )

        current_success = float(current.get("success_rate", 0.0))
        baseline_success = float(suite_baseline.get("success_rate", 0.0))
        success_floor = round(baseline_success * (1.0 - max_drop_fraction), 4)
        checks.append(
            {
                "name": f"{suite_key}_success_rate",
                "passed": current_success >= success_floor,
                "actual": current_success,
                "expected": f">= {success_floor}",
            }
        )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "baseline_generated_at": baseline.get("generated_at"),
        "max_drop_fraction": max_drop_fraction,
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare evaluation output to a committed baseline."
    )
    parser.add_argument("--report", type=Path, help="Path to an evaluation report JSON.")
    parser.add_argument(
        "--report-dir",
        type=Path,
        help="Directory containing all-supported-suites reports; the latest one will be used.",
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Write the baseline file from the supplied report instead of comparing.",
    )
    parser.add_argument("--max-drop-fraction", type=float, default=0.05)
    args = parser.parse_args()

    report_path = args.report or _latest_report(args.report_dir)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    if args.write_baseline:
        baseline = build_baseline_from_report(report, max_drop_fraction=args.max_drop_fraction)
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        args.baseline.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "baseline_path": str(args.baseline),
                    "suite": baseline["suite"],
                    "scenario_count": baseline["scenario_count"],
                    "overall_score": baseline["overall_score"],
                },
                indent=2,
            )
        )
        return

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    comparison = compare_report_to_baseline(report=report, baseline=baseline)
    print(
        json.dumps(
            {
                "baseline_path": str(args.baseline),
                "report_path": str(report_path),
                "passed": comparison["passed"],
                "checks": comparison["checks"],
            },
            indent=2,
        )
    )
    if not comparison["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
