from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from crewai_enterprise_pipeline_api.domain.models import (
    ComplianceMatrixSummary,
    LegalStructureSummary,
    TaxComplianceSummary,
)


class ComplianceLookupArgs(BaseModel):
    regulation: str | None = Field(
        default=None,
        description="Optional regulation name such as RBI NBFC Registration.",
    )


class ContractLookupArgs(BaseModel):
    contract_title: str | None = Field(
        default=None,
        description="Optional contract title substring to inspect.",
    )


class TaxLookupArgs(BaseModel):
    tax_area: str | None = Field(
        default=None,
        description="Optional tax area such as gst or transfer_pricing.",
    )


class ComplianceMatrixLookupTool(BaseTool):
    name: str = "review_compliance_matrix"
    description: str = "Inspect the structured compliance matrix for the current case."
    args_schema: type[BaseModel] = ComplianceLookupArgs
    summary: ComplianceMatrixSummary = Field(repr=False)

    def _run(self, regulation: str | None = None) -> str:
        items = self.summary.items
        if regulation:
            items = [item for item in items if regulation.lower() in item.regulation.lower()]
        if not items:
            return "No compliance-matrix item matched the requested filter."
        lines = []
        for item in items:
            evidence_note = (
                f"evidence_ids={', '.join(item.evidence_ids[:3])}"
                if item.evidence_ids
                else "evidence_ids=none"
            )
            header = (
                f"- {item.regulation} [{item.status.value}] via {item.regulator} | {evidence_note}"
            )
            lines.append(f"{header}\n  Notes: {item.notes}")
        return "\n".join(lines)


class ContractReviewLookupTool(BaseTool):
    name: str = "review_contract_clauses"
    description: str = "Inspect structured contract-review findings for the current case."
    args_schema: type[BaseModel] = ContractLookupArgs
    summary: LegalStructureSummary = Field(repr=False)

    def _run(self, contract_title: str | None = None) -> str:
        reviews = self.summary.contract_reviews
        if contract_title:
            reviews = [
                review
                for review in reviews
                if contract_title.lower() in review.contract_title.lower()
            ]
        if not reviews:
            return "No contract-review item matched the requested filter."
        lines = []
        for review in reviews:
            clauses = (
                ", ".join(clause.clause_key for clause in review.clauses if clause.present)
                or "no structured clauses detected"
            )
            header = (
                f"- {review.contract_title} ({review.contract_type}) | "
                f"governing_law={review.governing_law or 'unknown'}"
            )
            lines.append(
                f"{header}\n"
                f"  Clauses: {clauses}\n"
                f"  Flags: {', '.join(review.flags) if review.flags else 'none'}"
            )
        return "\n".join(lines)


class TaxComplianceLookupTool(BaseTool):
    name: str = "review_tax_compliance"
    description: str = "Inspect structured tax-compliance findings for the current case."
    args_schema: type[BaseModel] = TaxLookupArgs
    summary: TaxComplianceSummary = Field(repr=False)

    def _run(self, tax_area: str | None = None) -> str:
        items = self.summary.items
        if tax_area:
            items = [item for item in items if item.tax_area == tax_area]
        if not items:
            return "No tax-compliance item matched the requested filter."
        lines = []
        for item in items:
            evidence_note = (
                f"evidence_ids={', '.join(item.evidence_ids[:3])}"
                if item.evidence_ids
                else "evidence_ids=none"
            )
            lines.append(
                f"- {item.tax_area} [{item.status.value}] | {evidence_note}\n  Notes: {item.notes}"
            )
        if self.summary.gstins:
            lines.append(f"GSTINs: {', '.join(self.summary.gstins)}")
        return "\n".join(lines)


def build_compliance_tools(
    *,
    legal_summary: LegalStructureSummary | None,
    tax_summary: TaxComplianceSummary | None,
    compliance_summary: ComplianceMatrixSummary | None,
) -> list[BaseTool]:
    tools: list[BaseTool] = []
    if compliance_summary is not None and compliance_summary.items:
        tools.append(ComplianceMatrixLookupTool(summary=compliance_summary))
    if legal_summary is not None and legal_summary.contract_reviews:
        tools.append(ContractReviewLookupTool(summary=legal_summary))
    if tax_summary is not None and tax_summary.items:
        tools.append(TaxComplianceLookupTool(summary=tax_summary))
    return tools


def format_phase9_snapshot(
    *,
    legal_summary: LegalStructureSummary | None,
    tax_summary: TaxComplianceSummary | None,
    compliance_summary: ComplianceMatrixSummary | None,
) -> str:
    lines: list[str] = []
    if legal_summary is not None:
        lines.append(
            f"- Legal: directors={len(legal_summary.directors)}, "
            f"contract_reviews={len(legal_summary.contract_reviews)}, "
            f"charges={legal_summary.charges_detected}"
        )
        if legal_summary.flags:
            lines.append(f"- Legal flags: {'; '.join(legal_summary.flags[:3])}")
    if tax_summary is not None:
        known_items = [item for item in tax_summary.items if item.status.value != "unknown"]
        lines.append(
            f"- Tax: gstins={len(tax_summary.gstins)}, areas_with_evidence={len(known_items)}"
        )
        if tax_summary.flags:
            lines.append(f"- Tax flags: {'; '.join(tax_summary.flags[:3])}")
    if compliance_summary is not None:
        known_items = [item for item in compliance_summary.items if item.status.value != "unknown"]
        lines.append(
            f"- Regulatory: matrix_items={len(compliance_summary.items)}, "
            f"known_statuses={len(known_items)}"
        )
        if compliance_summary.flags:
            lines.append(f"- Regulatory flags: {'; '.join(compliance_summary.flags[:3])}")
    return "\n".join(lines) if lines else "No structured Phase 9 compliance state is available yet."
