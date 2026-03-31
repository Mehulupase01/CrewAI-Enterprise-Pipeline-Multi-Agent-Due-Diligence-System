from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from crewai_enterprise_pipeline_api.domain.models import (
    BfsiNbfcMetricsSummary,
    ManufacturingMetricsSummary,
    TechSaasMetricsSummary,
)


class TechSaasLookupArgs(BaseModel):
    focus: str | None = Field(
        default=None,
        description="Optional focus: revenue, retention, unit_economics, or flags.",
    )


class ManufacturingLookupArgs(BaseModel):
    focus: str | None = Field(
        default=None,
        description="Optional focus: capacity, working_capital, assets, or flags.",
    )


class BfsiNbfcLookupArgs(BaseModel):
    focus: str | None = Field(
        default=None,
        description="Optional focus: asset_quality, capital, liquidity, psl, or flags.",
    )


class TechSaasMetricsTool(BaseTool):
    name: str = "review_tech_saas_metrics"
    description: str = "Inspect structured Tech/SaaS ARR, retention, and unit-economics metrics."
    args_schema: type[BaseModel] = TechSaasLookupArgs
    summary: TechSaasMetricsSummary = Field(repr=False)

    def _run(self, focus: str | None = None) -> str:
        focus_key = (focus or "").strip().lower()
        lines = []
        if focus_key in {"", "revenue"}:
            if self.summary.arr is not None:
                lines.append(f"ARR: {self.summary.arr:.2f}")
            if self.summary.mrr is not None:
                lines.append(f"MRR: {self.summary.mrr:.2f}")
            if self.summary.arr_waterfall:
                lines.append("ARR waterfall:")
                for item in self.summary.arr_waterfall[:6]:
                    lines.append(f"- {item.label}: {item.amount:.2f} | {item.note}")
        if focus_key in {"", "retention"}:
            if self.summary.nrr is not None:
                lines.append(f"NRR: {self.summary.nrr:.0%}")
            if self.summary.churn_rate is not None:
                lines.append(f"Churn: {self.summary.churn_rate:.0%}")
        if focus_key in {"", "unit_economics"}:
            if self.summary.ltv is not None:
                lines.append(f"LTV: {self.summary.ltv:.2f}")
            if self.summary.cac is not None:
                lines.append(f"CAC: {self.summary.cac:.2f}")
            if self.summary.payback_months is not None:
                lines.append(f"Payback: {self.summary.payback_months:.1f} months")
        if focus_key in {"", "flags"} and self.summary.flags:
            lines.append("Flags:")
            lines.extend(f"- {flag}" for flag in self.summary.flags[:5])
        return "\n".join(lines) if lines else "No structured Tech/SaaS metrics are available."


class ManufacturingMetricsTool(BaseTool):
    name: str = "review_manufacturing_metrics"
    description: str = (
        "Inspect structured manufacturing capacity, working-capital, "
        "and asset metrics."
    )
    args_schema: type[BaseModel] = ManufacturingLookupArgs
    summary: ManufacturingMetricsSummary = Field(repr=False)

    def _run(self, focus: str | None = None) -> str:
        focus_key = (focus or "").strip().lower()
        lines = []
        if focus_key in {"", "capacity"} and self.summary.capacity_utilization is not None:
            lines.append(f"Capacity utilization: {self.summary.capacity_utilization:.0%}")
        if focus_key in {"", "working_capital"}:
            if self.summary.dio is not None:
                lines.append(f"DIO: {self.summary.dio:.1f} days")
            if self.summary.dso is not None:
                lines.append(f"DSO: {self.summary.dso:.1f} days")
            if self.summary.dpo is not None:
                lines.append(f"DPO: {self.summary.dpo:.1f} days")
            if self.summary.asset_turnover is not None:
                lines.append(f"Asset turnover: {self.summary.asset_turnover:.2f}x")
        if focus_key in {"", "assets"} and self.summary.asset_register:
            lines.append("Asset register:")
            for item in self.summary.asset_register[:6]:
                carrying = "n/a" if item.carrying_value is None else f"{item.carrying_value:.2f}"
                replacement = (
                    "n/a" if item.replacement_cost is None else f"{item.replacement_cost:.2f}"
                )
                gap = "n/a" if item.replacement_gap is None else f"{item.replacement_gap:.2f}"
                lines.append(
                    "- "
                    f"{item.asset_name}: carrying={carrying} | "
                    f"replacement={replacement} | gap={gap}"
                )
        if focus_key in {"", "flags"} and self.summary.flags:
            lines.append("Flags:")
            lines.extend(f"- {flag}" for flag in self.summary.flags[:5])
        if not lines and self.summary.asset_register:
            for item in self.summary.asset_register[:6]:
                carrying = "n/a" if item.carrying_value is None else f"{item.carrying_value:.2f}"
                replacement = (
                    "n/a" if item.replacement_cost is None else f"{item.replacement_cost:.2f}"
                )
                gap = "n/a" if item.replacement_gap is None else f"{item.replacement_gap:.2f}"
                lines.append(
                    "- "
                    f"{item.asset_name}: carrying={carrying} | "
                    f"replacement={replacement} | gap={gap}"
                )
        return "\n".join(lines) if lines else "No structured manufacturing metrics are available."


class BfsiNbfcMetricsTool(BaseTool):
    name: str = "review_bfsi_nbfc_metrics"
    description: str = "Inspect structured BFSI/NBFC asset-quality, capital, and ALM metrics."
    args_schema: type[BaseModel] = BfsiNbfcLookupArgs
    summary: BfsiNbfcMetricsSummary = Field(repr=False)

    def _run(self, focus: str | None = None) -> str:
        focus_key = (focus or "").strip().lower()
        lines = []
        if focus_key in {"", "asset_quality"}:
            if self.summary.gnpa is not None:
                lines.append(f"GNPA: {self.summary.gnpa:.2%}")
            if self.summary.nnpa is not None:
                lines.append(f"NNPA: {self.summary.nnpa:.2%}")
        if focus_key in {"", "capital"} and self.summary.crar is not None:
            lines.append(f"CRAR: {self.summary.crar:.2%}")
        if focus_key in {"", "liquidity"}:
            if self.summary.alm_mismatch is not None:
                lines.append(f"ALM mismatch: {self.summary.alm_mismatch:.2%}")
            if self.summary.alm_bucket_gaps:
                lines.append("ALM buckets:")
                for item in self.summary.alm_bucket_gaps[:6]:
                    lines.append(f"- {item.bucket_label}: {item.mismatch_ratio:.2%} | {item.note}")
        if focus_key in {"", "psl"}:
            lines.append(f"PSL compliance: {self.summary.psl_compliance.value}")
        if focus_key in {"", "flags"} and self.summary.flags:
            lines.append("Flags:")
            lines.extend(f"- {flag}" for flag in self.summary.flags[:5])
        return "\n".join(lines) if lines else "No structured BFSI/NBFC metrics are available."


def build_phase12_tools(
    *,
    sector_pack: str,
    tech_saas_metrics: TechSaasMetricsSummary | None = None,
    manufacturing_metrics: ManufacturingMetricsSummary | None = None,
    bfsi_nbfc_metrics: BfsiNbfcMetricsSummary | None = None,
) -> list[BaseTool]:
    if sector_pack == "tech_saas_services" and tech_saas_metrics is not None:
        return [TechSaasMetricsTool(summary=tech_saas_metrics)]
    if sector_pack == "manufacturing_industrials" and manufacturing_metrics is not None:
        return [ManufacturingMetricsTool(summary=manufacturing_metrics)]
    if sector_pack == "bfsi_nbfc" and bfsi_nbfc_metrics is not None:
        return [BfsiNbfcMetricsTool(summary=bfsi_nbfc_metrics)]
    return []


def format_phase12_snapshot(
    *,
    sector_pack: str,
    tech_saas_metrics: TechSaasMetricsSummary | None = None,
    manufacturing_metrics: ManufacturingMetricsSummary | None = None,
    bfsi_nbfc_metrics: BfsiNbfcMetricsSummary | None = None,
) -> str:
    if sector_pack == "tech_saas_services" and tech_saas_metrics is not None:
        arr_line = (
            f"- ARR: {tech_saas_metrics.arr:.2f}"
            if tech_saas_metrics.arr is not None
            else "- ARR: n/a"
        )
        mrr_line = (
            f"- MRR: {tech_saas_metrics.mrr:.2f}"
            if tech_saas_metrics.mrr is not None
            else "- MRR: n/a"
        )
        nrr_line = (
            f"- NRR: {tech_saas_metrics.nrr:.0%}"
            if tech_saas_metrics.nrr is not None
            else "- NRR: n/a"
        )
        return "\n".join(
            [
                arr_line,
                mrr_line,
                nrr_line,
                (
                    f"- Churn: {tech_saas_metrics.churn_rate:.0%}"
                    if tech_saas_metrics.churn_rate is not None
                    else "- Churn: n/a"
                ),
                (
                    f"- Payback: {tech_saas_metrics.payback_months:.1f} months"
                    if tech_saas_metrics.payback_months is not None
                    else "- Payback: n/a"
                ),
            ]
        )
    if sector_pack == "manufacturing_industrials" and manufacturing_metrics is not None:
        return "\n".join(
            [
                (
                    f"- Capacity utilization: {manufacturing_metrics.capacity_utilization:.0%}"
                    if manufacturing_metrics.capacity_utilization is not None
                    else "- Capacity utilization: n/a"
                ),
                f"- DIO: {manufacturing_metrics.dio:.1f} days"
                if manufacturing_metrics.dio is not None
                else "- DIO: n/a",
                f"- DSO: {manufacturing_metrics.dso:.1f} days"
                if manufacturing_metrics.dso is not None
                else "- DSO: n/a",
                f"- DPO: {manufacturing_metrics.dpo:.1f} days"
                if manufacturing_metrics.dpo is not None
                else "- DPO: n/a",
                (
                    f"- Asset register findings: {len(manufacturing_metrics.asset_register)}"
                ),
            ]
        )
    if sector_pack == "bfsi_nbfc" and bfsi_nbfc_metrics is not None:
        return "\n".join(
            [
                f"- GNPA: {bfsi_nbfc_metrics.gnpa:.2%}"
                if bfsi_nbfc_metrics.gnpa is not None
                else "- GNPA: n/a",
                f"- NNPA: {bfsi_nbfc_metrics.nnpa:.2%}"
                if bfsi_nbfc_metrics.nnpa is not None
                else "- NNPA: n/a",
                f"- CRAR: {bfsi_nbfc_metrics.crar:.2%}"
                if bfsi_nbfc_metrics.crar is not None
                else "- CRAR: n/a",
                f"- ALM mismatch: {bfsi_nbfc_metrics.alm_mismatch:.2%}"
                if bfsi_nbfc_metrics.alm_mismatch is not None
                else "- ALM mismatch: n/a",
                f"- PSL compliance: {bfsi_nbfc_metrics.psl_compliance.value}",
            ]
        )
    return "No structured Phase 12 sector-pack state is available yet."
