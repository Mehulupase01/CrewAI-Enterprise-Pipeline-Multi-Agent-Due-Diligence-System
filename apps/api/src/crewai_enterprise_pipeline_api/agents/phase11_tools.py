from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from crewai_enterprise_pipeline_api.domain.models import (
    BorrowerScorecard,
    BuySideAnalysis,
    VendorRiskTier,
)


class BuySideLookupArgs(BaseModel):
    focus: str | None = Field(
        default=None,
        description="Optional focus: valuation, spa, pmi, or flags.",
    )


class CreditLookupArgs(BaseModel):
    section: str | None = Field(
        default=None,
        description="Optional section: financial_health, collateral, covenants, or tracking.",
    )


class VendorLookupArgs(BaseModel):
    focus: str | None = Field(
        default=None,
        description="Optional focus: tier, questionnaire, certifications, or flags.",
    )


class BuySidePackLookupTool(BaseTool):
    name: str = "review_buy_side_pack"
    description: str = (
        "Inspect structured buy-side valuation bridge, SPA issues, and PMI risks."
    )
    args_schema: type[BaseModel] = BuySideLookupArgs
    summary: BuySideAnalysis = Field(repr=False)

    def _run(self, focus: str | None = None) -> str:
        focus_key = (focus or "").strip().lower()
        lines: list[str] = []
        if focus_key in {"", "valuation"}:
            lines.append("Valuation bridge:")
            for item in self.summary.valuation_bridge[:6]:
                amount = "n/a" if item.amount is None else f"{item.amount:.2f}"
                lines.append(f"- {item.label} [{item.category}] amount={amount} | {item.impact}")
        if focus_key in {"", "spa"}:
            lines.append("SPA issues:")
            for item in self.summary.spa_issues[:6]:
                lines.append(
                    f"- {item.title} [{item.severity.value}] | {item.rationale} | "
                    f"Recommendation: {item.recommendation}"
                )
        if focus_key in {"", "pmi"}:
            lines.append("PMI risks:")
            for item in self.summary.pmi_risks[:6]:
                lines.append(
                    f"- {item.area} [{item.severity.value}] | {item.description} | "
                    f"Day 1: {item.day_one_action}"
                )
        if focus_key in {"", "flags"} and self.summary.flags:
            lines.append("Flags:")
            lines.extend(f"- {flag}" for flag in self.summary.flags[:4])
        return "\n".join(lines) if lines else "No structured buy-side pack summary is available."


class CreditPackLookupTool(BaseTool):
    name: str = "review_borrower_scorecard"
    description: str = (
        "Inspect structured borrower scorecard, covenant tracking, and collateral posture."
    )
    args_schema: type[BaseModel] = CreditLookupArgs
    summary: BorrowerScorecard = Field(repr=False)

    def _run(self, section: str | None = None) -> str:
        focus = (section or "").strip().lower()
        lines = [f"Overall score: {self.summary.overall_score}/100 ({self.summary.overall_rating})"]
        sections = {
            "financial_health": self.summary.financial_health,
            "collateral": self.summary.collateral,
            "covenants": self.summary.covenants,
        }
        if focus in {"", "financial_health", "collateral", "covenants"}:
            for key, value in sections.items():
                if focus and key != focus:
                    continue
                lines.append(f"- {key}: {value.score}/100 ({value.rating}) | {value.rationale}")
                if value.flags:
                    lines.extend(f"  - flag: {flag}" for flag in value.flags[:3])
        if focus in {"", "tracking"} and self.summary.covenant_tracking:
            lines.append("Covenant tracking:")
            for item in self.summary.covenant_tracking[:6]:
                lines.append(
                    f"- {item.name} [{item.status}] | threshold={item.threshold or 'n/a'} "
                    f"| current={item.current_value or 'n/a'} | {item.note}"
                )
        return "\n".join(lines)


class VendorPackLookupTool(BaseTool):
    name: str = "review_vendor_risk_tier"
    description: str = (
        "Inspect structured vendor risk tier, questionnaire, and certification gaps."
    )
    args_schema: type[BaseModel] = VendorLookupArgs
    summary: VendorRiskTier = Field(repr=False)

    def _run(self, focus: str | None = None) -> str:
        focus_key = (focus or "").strip().lower()
        lines = [
            f"Vendor tier: {self.summary.tier}",
            f"Overall score: {self.summary.overall_score}/100",
            f"Next review date: {self.summary.next_review_date.isoformat()}",
        ]
        if focus_key in {"", "tier"}:
            lines.append("Scoring breakdown:")
            for item in self.summary.scoring_breakdown:
                lines.append(
                    f"- {item.factor}: {item.score}/100 "
                    f"@ weight {item.weight:.2f} | {item.rationale}"
                )
        if focus_key in {"", "questionnaire"}:
            lines.append("Questionnaire:")
            for item in self.summary.questionnaire:
                lines.append(f"- {item.section} [{item.status}] | {item.detail}")
        if focus_key in {"", "certifications"}:
            required = ", ".join(self.summary.certifications_required) or "none"
            lines.append(f"Outstanding certifications: {required}")
        if focus_key in {"", "flags"} and self.summary.flags:
            lines.append("Flags:")
            lines.extend(f"- {flag}" for flag in self.summary.flags[:4])
        return "\n".join(lines)


def build_phase11_tools(
    *,
    motion_pack: str,
    buy_side_analysis: BuySideAnalysis | None = None,
    borrower_scorecard: BorrowerScorecard | None = None,
    vendor_risk_tier: VendorRiskTier | None = None,
) -> list[BaseTool]:
    if motion_pack == "buy_side_diligence" and buy_side_analysis is not None:
        return [BuySidePackLookupTool(summary=buy_side_analysis)]
    if motion_pack == "credit_lending" and borrower_scorecard is not None:
        return [CreditPackLookupTool(summary=borrower_scorecard)]
    if motion_pack == "vendor_onboarding" and vendor_risk_tier is not None:
        return [VendorPackLookupTool(summary=vendor_risk_tier)]
    return []


def format_phase11_snapshot(
    *,
    motion_pack: str,
    buy_side_analysis: BuySideAnalysis | None = None,
    borrower_scorecard: BorrowerScorecard | None = None,
    vendor_risk_tier: VendorRiskTier | None = None,
) -> str:
    if motion_pack == "buy_side_diligence" and buy_side_analysis is not None:
        top_flags = "; ".join(buy_side_analysis.flags[:3]) if buy_side_analysis.flags else "none"
        return "\n".join(
            [
                f"- Valuation bridge items: {len(buy_side_analysis.valuation_bridge)}",
                f"- SPA issues: {len(buy_side_analysis.spa_issues)}",
                f"- PMI risks: {len(buy_side_analysis.pmi_risks)}",
                f"- Flags: {top_flags}",
            ]
        )
    if motion_pack == "credit_lending" and borrower_scorecard is not None:
        return "\n".join(
            [
                f"- Overall borrower score: {borrower_scorecard.overall_score}/100",
                f"- Financial health: {borrower_scorecard.financial_health.score}/100",
                f"- Collateral: {borrower_scorecard.collateral.score}/100",
                f"- Covenants: {borrower_scorecard.covenants.score}/100",
                f"- Covenant items: {len(borrower_scorecard.covenant_tracking)}",
            ]
        )
    if motion_pack == "vendor_onboarding" and vendor_risk_tier is not None:
        return "\n".join(
            [
                f"- Vendor tier: {vendor_risk_tier.tier}",
                f"- Overall score: {vendor_risk_tier.overall_score}/100",
                f"- Questionnaire sections: {len(vendor_risk_tier.questionnaire)}",
                (
                    "- Outstanding certifications: "
                    + (", ".join(vendor_risk_tier.certifications_required) or "none")
                ),
            ]
        )
    return "No structured Phase 11 motion-pack state is available yet."
