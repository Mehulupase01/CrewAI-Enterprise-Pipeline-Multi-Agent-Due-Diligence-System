"""Pydantic models for structured CrewAI agent output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WorkstreamAnalysisOutput(BaseModel):
    """Structured output from a workstream analyst agent."""

    status: str = Field(
        description=(
            "Workstream status. Must be one of: ready_for_review, needs_follow_up, blocked"
        ),
    )
    headline: str = Field(
        description="One-line summary of the workstream status and key finding.",
    )
    narrative: str = Field(
        description=(
            "2-4 paragraph analysis covering: key evidence reviewed, "
            "material findings, risk assessment, and gaps in information."
        ),
    )
    finding_count: int = Field(
        description="Number of significant findings identified in this workstream.",
    )
    blocker_count: int = Field(
        description="Number of blocking issues that must be resolved before sign-off.",
    )
    confidence: float = Field(
        description="Confidence in the analysis from 0.0 (no data) to 1.0 (complete).",
    )
    recommended_next_action: str = Field(
        description="Single most important next action for this workstream.",
    )


class ExecutiveSummaryOutput(BaseModel):
    """Structured output from the coordinator agent."""

    executive_summary: str = Field(
        description=(
            "3-5 paragraph executive summary synthesizing all workstream findings. "
            "Cover overall risk posture, key deal considerations, and readiness."
        ),
    )
    overall_risk_assessment: str = Field(
        description="Overall risk level: low, medium, high, or critical.",
    )
    top_risks: list[str] = Field(
        description="Top 3-5 material risk items across all workstreams.",
    )
    recommended_next_steps: list[str] = Field(
        description="Top 3-5 recommended next steps for the review committee.",
    )


class MotionPackAnalysisOutput(BaseModel):
    """Structured output from the Phase 11 motion-pack specialist agent."""

    status: str = Field(
        description="Motion-pack status. Must be ready_for_review, needs_follow_up, or blocked.",
    )
    headline: str = Field(
        description="One-line summary of the motion-pack posture.",
    )
    narrative: str = Field(
        description=(
            "2-4 paragraph analysis focused on the motion-pack specific outputs such as "
            "valuation bridge, borrower scorecard, or vendor risk tier."
        ),
    )
    key_items: list[str] = Field(
        description="Top 3-6 motion-pack findings or decision points.",
    )
    recommended_actions: list[str] = Field(
        description="Top 3-5 recommended follow-up actions for the motion pack.",
    )
