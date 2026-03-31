from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from crewai_enterprise_pipeline_api.domain.models import FinancialMetricSummary

SECTOR_BENCHMARKS: dict[str, dict[str, tuple[float, float, str]]] = {
    "tech_saas_services": {
        "ebitda_margin": (0.10, 0.25, "fraction of revenue"),
        "cash_conversion": (0.70, 1.10, "operating cash flow / EBITDA"),
        "working_capital_days": (-30.0, 60.0, "days"),
        "revenue_growth_latest_yoy": (0.12, 0.35, "year-on-year growth"),
    },
    "manufacturing_industrials": {
        "ebitda_margin": (0.08, 0.18, "fraction of revenue"),
        "cash_conversion": (0.60, 1.00, "operating cash flow / EBITDA"),
        "working_capital_days": (60.0, 150.0, "days"),
        "asset_turnover": (1.00, 2.50, "revenue / total assets"),
    },
    "bfsi_nbfc": {
        "return_on_assets": (0.01, 0.04, "PAT / total assets"),
        "return_on_equity": (0.08, 0.18, "PAT / equity"),
        "interest_coverage": (1.50, 4.00, "EBITDA / interest expense"),
        "debt_to_equity": (3.00, 8.00, "net debt / equity"),
    },
}


class FinancialRatioLookupArgs(BaseModel):
    metric: str | None = Field(
        default=None,
        description="Optional metric key such as ebitda_margin or revenue_cagr_3y.",
    )
    period_label: str | None = Field(
        default=None,
        description="Optional period label such as FY25.",
    )


class BenchmarkLookupArgs(BaseModel):
    metric: str | None = Field(
        default=None,
        description="Optional metric key to retrieve sector benchmarks for.",
    )


class FinancialRatioLookupTool(BaseTool):
    name: str = "review_financial_ratios"
    description: str = "Inspect parsed financial periods, ratios, and QoE adjustments."
    args_schema: type[BaseModel] = FinancialRatioLookupArgs
    summary: FinancialMetricSummary = Field(repr=False)

    def _run(self, metric: str | None = None, period_label: str | None = None) -> str:
        lines: list[str] = []
        if metric:
            value = self.summary.ratios.get(metric)
            if value is None:
                return f"Metric '{metric}' is not available in the current financial summary."
            lines.append(f"Ratio {metric}: {value:.4f}")
        else:
            if self.summary.ratios:
                lines.append("Ratios:")
                for key, value in sorted(self.summary.ratios.items()):
                    rendered = "n/a" if value is None else f"{value:.4f}"
                    lines.append(f"- {key}: {rendered}")

        if period_label:
            period = next(
                (
                    item
                    for item in self.summary.periods
                    if item.label.lower() == period_label.lower()
                ),
                None,
            )
            if period is None:
                return f"Period '{period_label}' is not available in the current financial summary."
            lines.append("")
            lines.append(f"Period {period.label}:")
            for key, value in period.model_dump(exclude_none=True).items():
                if key == "label":
                    continue
                lines.append(f"- {key}: {value}")
        elif self.summary.periods:
            latest = self.summary.periods[-1]
            lines.append("")
            lines.append(f"Latest period snapshot ({latest.label}):")
            for key, value in latest.model_dump(exclude_none=True).items():
                if key == "label":
                    continue
                lines.append(f"- {key}: {value}")

        if self.summary.qoe_adjustments:
            lines.append("")
            lines.append("QoE adjustments:")
            for adjustment in self.summary.qoe_adjustments:
                lines.append(
                    f"- {adjustment.label} ({adjustment.category}): {adjustment.amount:.4f}"
                )

        if self.summary.normalized_ebitda is not None:
            lines.append("")
            lines.append(f"Normalized EBITDA: {self.summary.normalized_ebitda:.4f}")

        if not lines:
            return "No parsed financial ratios are available for this case."
        return "\n".join(lines)


class BenchmarkLookupTool(BaseTool):
    name: str = "lookup_financial_benchmarks"
    description: str = "Look up sector-aligned benchmark ranges for core financial metrics."
    args_schema: type[BaseModel] = BenchmarkLookupArgs
    sector_pack: str

    def _run(self, metric: str | None = None) -> str:
        benchmarks = SECTOR_BENCHMARKS.get(self.sector_pack, {})
        if not benchmarks:
            return f"No benchmark ranges are configured for sector pack '{self.sector_pack}'."

        if metric:
            entry = benchmarks.get(metric)
            if entry is None:
                return f"No benchmark is configured for metric '{metric}' in {self.sector_pack}."
            low, high, unit = entry
            return (
                f"{metric} benchmark for {self.sector_pack}: low={low:.4f}, "
                f"high={high:.4f}, unit={unit}."
            )

        lines = [f"Benchmarks for {self.sector_pack}:"]
        for key, (low, high, unit) in sorted(benchmarks.items()):
            lines.append(f"- {key}: {low:.4f} to {high:.4f} ({unit})")
        return "\n".join(lines)


def build_financial_tools(
    *,
    financial_summary: FinancialMetricSummary | None,
    sector_pack: str,
) -> list[BaseTool]:
    if financial_summary is None or not financial_summary.periods:
        return []
    return [
        FinancialRatioLookupTool(summary=financial_summary),
        BenchmarkLookupTool(sector_pack=sector_pack),
    ]


def format_financial_snapshot(summary: FinancialMetricSummary | None) -> str:
    if summary is None or not summary.periods:
        return "No structured financial summary is available yet."

    latest = summary.periods[-1]
    lines = [
        f"- Parsed periods: {', '.join(period.label for period in summary.periods)}",
        f"- Latest period: {latest.label}",
    ]
    if latest.revenue is not None:
        lines.append(f"- Latest revenue: {latest.revenue:.2f}")
    if latest.ebitda is not None:
        lines.append(f"- Reported EBITDA: {latest.ebitda:.2f}")
    if summary.normalized_ebitda is not None:
        lines.append(f"- Normalized EBITDA: {summary.normalized_ebitda:.2f}")
    for key in ("revenue_cagr_3y", "ebitda_margin", "cash_conversion", "debt_to_ebitda"):
        value = summary.ratios.get(key)
        if value is not None:
            lines.append(f"- {key}: {value:.4f}")
    if summary.flags:
        lines.append(f"- Flags: {'; '.join(summary.flags[:4])}")
    return "\n".join(lines)


def benchmark_status_for_metric(
    *,
    sector_pack: str,
    metric: str,
    value: float | None,
) -> str | None:
    if value is None:
        return None
    benchmark = SECTOR_BENCHMARKS.get(sector_pack, {}).get(metric)
    if benchmark is None:
        return None
    low, high, _ = benchmark
    if value < low:
        return "below benchmark"
    if value > high:
        return "above benchmark"
    return "within benchmark"
