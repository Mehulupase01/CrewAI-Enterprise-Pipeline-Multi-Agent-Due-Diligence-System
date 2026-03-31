from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from crewai_enterprise_pipeline_api.domain.models import (
    CommercialSummary,
    CyberPrivacySummary,
    ForensicSummary,
    OperationsSummary,
)


class CommercialLookupArgs(BaseModel):
    focus: str | None = Field(
        default=None,
        description="Optional focus such as concentration, renewal, pricing, nrr, or churn.",
    )


class OperationsLookupArgs(BaseModel):
    dependency_type: str | None = Field(
        default=None,
        description="Optional dependency type such as supply_chain, key_person, site, or capacity.",
    )


class CyberLookupArgs(BaseModel):
    control_key: str | None = Field(
        default=None,
        description="Optional control key such as consent_mechanism or iso_27001.",
    )


class ForensicLookupArgs(BaseModel):
    flag_type: str | None = Field(
        default=None,
        description="Optional flag type such as RELATED_PARTY or ROUND_TRIPPING.",
    )


class CommercialSignalLookupTool(BaseTool):
    name: str = "review_commercial_signals"
    description: str = (
        "Inspect structured commercial concentration, churn, pricing, and renewal "
        "findings."
    )
    args_schema: type[BaseModel] = CommercialLookupArgs
    summary: CommercialSummary = Field(repr=False)

    def _run(self, focus: str | None = None) -> str:
        focus_key = (focus or "").strip().lower()
        lines: list[str] = []
        if focus_key in {"", "concentration"}:
            if self.summary.concentration_signals:
                lines.append("Concentration signals:")
                for signal in self.summary.concentration_signals[:5]:
                    lines.append(
                        f"- {signal.subject}: {signal.share_of_revenue:.0%} "
                        f"({signal.category}) | "
                        f"evidence={','.join(signal.evidence_ids[:3]) or 'none'}"
                    )
            elif focus_key == "concentration":
                return "No commercial concentration signals are available."
        if focus_key in {"", "nrr"} and self.summary.net_revenue_retention is not None:
            lines.append(f"NRR: {self.summary.net_revenue_retention:.0%}")
        if focus_key in {"", "churn"} and self.summary.churn_rate is not None:
            lines.append(f"Churn: {self.summary.churn_rate:.0%}")
        if focus_key in {"", "pricing"} and self.summary.pricing_signals:
            lines.append("Pricing signals:")
            lines.extend(f"- {signal}" for signal in self.summary.pricing_signals[:4])
        if focus_key in {"", "renewal"} and self.summary.renewal_signals:
            lines.append("Renewal signals:")
            for signal in self.summary.renewal_signals[:5]:
                counterparty = signal.counterparty or "unknown counterparty"
                lines.append(f"- {counterparty} [{signal.status}]: {signal.note}")
        if self.summary.flags and focus_key in {"", "flags"}:
            lines.append("Flags:")
            lines.extend(f"- {flag}" for flag in self.summary.flags[:4])
        if not lines:
            return "No structured commercial signals are available."
        return "\n".join(lines)


class OperationsRiskLookupTool(BaseTool):
    name: str = "review_operations_risks"
    description: str = (
        "Inspect structured operations dependency, continuity, and supplier findings."
    )
    args_schema: type[BaseModel] = OperationsLookupArgs
    summary: OperationsSummary = Field(repr=False)

    def _run(self, dependency_type: str | None = None) -> str:
        signals = self.summary.dependency_signals
        if dependency_type:
            signals = [
                signal
                for signal in signals
                if signal.dependency_type == dependency_type
            ]
        if not signals and self.summary.supplier_concentration_top_3 is None:
            return "No structured operations risks are available."

        lines: list[str] = []
        if self.summary.supplier_concentration_top_3 is not None:
            lines.append(
                f"Supplier concentration: {self.summary.supplier_concentration_top_3:.0%}"
            )
        for signal in signals[:6]:
            lines.append(
                f"- {signal.label} [{signal.dependency_type}] | "
                f"evidence={','.join(signal.evidence_ids[:3]) or 'none'}\n"
                f"  {signal.detail}"
            )
        if self.summary.flags:
            lines.append("Flags:")
            lines.extend(f"- {flag}" for flag in self.summary.flags[:4])
        return "\n".join(lines)


class CyberControlLookupTool(BaseTool):
    name: str = "review_cyber_controls"
    description: str = "Inspect structured DPDP, security certification, and breach findings."
    args_schema: type[BaseModel] = CyberLookupArgs
    summary: CyberPrivacySummary = Field(repr=False)

    def _run(self, control_key: str | None = None) -> str:
        controls = self.summary.controls
        if control_key:
            controls = [item for item in controls if item.control_key == control_key]
        if not controls:
            return "No structured cyber or privacy controls matched the requested filter."

        lines = []
        for control in controls:
            lines.append(
                f"- {control.control_key} [{control.status.value}] | "
                f"evidence={','.join(control.evidence_ids[:3]) or 'none'}\n"
                f"  Notes: {control.notes}"
            )
        if self.summary.certifications:
            lines.append("Certifications: " + ", ".join(self.summary.certifications))
        if self.summary.breach_history:
            lines.append("Breach history:")
            lines.extend(f"- {item}" for item in self.summary.breach_history[:4])
        return "\n".join(lines)


class ForensicFlagLookupTool(BaseTool):
    name: str = "review_forensic_flags"
    description: str = "Inspect structured forensic red flags and supporting evidence references."
    args_schema: type[BaseModel] = ForensicLookupArgs
    summary: ForensicSummary = Field(repr=False)

    def _run(self, flag_type: str | None = None) -> str:
        flags = self.summary.flags
        if flag_type:
            flags = [flag for flag in flags if flag.flag_type.value == flag_type]
        if not flags:
            return "No structured forensic flags matched the requested filter."

        return "\n".join(
            f"- {flag.flag_type.value} [{flag.severity.value}] | "
            f"evidence={','.join(flag.evidence_ids[:3]) or 'none'}\n"
            f"  {flag.description}"
            for flag in flags
        )


def build_phase10_tools(
    *,
    commercial_summary: CommercialSummary | None,
    operations_summary: OperationsSummary | None,
    cyber_summary: CyberPrivacySummary | None,
    forensic_summary: ForensicSummary | None,
) -> list[BaseTool]:
    tools: list[BaseTool] = []
    if commercial_summary is not None and (
        commercial_summary.concentration_signals
        or commercial_summary.renewal_signals
        or commercial_summary.pricing_signals
        or commercial_summary.flags
    ):
        tools.append(CommercialSignalLookupTool(summary=commercial_summary))
    if operations_summary is not None and (
        operations_summary.dependency_signals
        or operations_summary.flags
        or operations_summary.supplier_concentration_top_3 is not None
    ):
        tools.append(OperationsRiskLookupTool(summary=operations_summary))
    known_cyber_controls = (
        []
        if cyber_summary is None
        else [item for item in cyber_summary.controls if item.status.value != "unknown"]
    )
    if cyber_summary is not None and (
        known_cyber_controls
        or cyber_summary.certifications
        or cyber_summary.breach_history
    ):
        tools.append(CyberControlLookupTool(summary=cyber_summary))
    if forensic_summary is not None and forensic_summary.flags:
        tools.append(ForensicFlagLookupTool(summary=forensic_summary))
    return tools


def format_phase10_snapshot(
    *,
    commercial_summary: CommercialSummary | None,
    operations_summary: OperationsSummary | None,
    cyber_summary: CyberPrivacySummary | None,
    forensic_summary: ForensicSummary | None,
) -> str:
    lines: list[str] = []
    if commercial_summary is not None:
        lines.append(
            f"- Commercial: concentration={len(commercial_summary.concentration_signals)}, "
            f"renewals={len(commercial_summary.renewal_signals)}"
        )
        if commercial_summary.net_revenue_retention is not None:
            lines.append(f"- Commercial NRR: {commercial_summary.net_revenue_retention:.0%}")
        if commercial_summary.churn_rate is not None:
            lines.append(f"- Commercial churn: {commercial_summary.churn_rate:.0%}")
        if commercial_summary.flags:
            lines.append(f"- Commercial flags: {'; '.join(commercial_summary.flags[:3])}")
    if operations_summary is not None:
        lines.append(
            f"- Operations: dependencies={len(operations_summary.dependency_signals)}, "
            f"single_site={operations_summary.single_site_dependency}"
        )
        if operations_summary.supplier_concentration_top_3 is not None:
            lines.append(
                f"- Supplier concentration: {operations_summary.supplier_concentration_top_3:.0%}"
            )
        if operations_summary.flags:
            lines.append(f"- Operations flags: {'; '.join(operations_summary.flags[:3])}")
    if cyber_summary is not None:
        known_controls = [
            control for control in cyber_summary.controls if control.status.value != "unknown"
        ]
        lines.append(
            f"- Cyber: controls_with_evidence={len(known_controls)}, "
            f"certifications={len(cyber_summary.certifications)}"
        )
        if cyber_summary.flags:
            lines.append(f"- Cyber flags: {'; '.join(cyber_summary.flags[:3])}")
    if forensic_summary is not None:
        lines.append(f"- Forensic: flags={len(forensic_summary.flags)}")
        if forensic_summary.flags:
            lines.append(
                "- Forensic flag types: "
                + ", ".join(flag.flag_type.value for flag in forensic_summary.flags[:4])
            )
    return "\n".join(lines) if lines else "No structured Phase 10 state is available yet."
