"""Scoped read-only CrewAI tools backed by pre-loaded case snapshots."""

from __future__ import annotations

import re
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from crewai_enterprise_pipeline_api.agents.compliance_tools import (
    build_compliance_tools,
)
from crewai_enterprise_pipeline_api.agents.financial_tools import build_financial_tools
from crewai_enterprise_pipeline_api.agents.phase10_tools import build_phase10_tools
from crewai_enterprise_pipeline_api.agents.phase11_tools import build_phase11_tools
from crewai_enterprise_pipeline_api.agents.phase12_tools import build_phase12_tools
from crewai_enterprise_pipeline_api.domain.models import (
    BfsiNbfcMetricsSummary,
    BorrowerScorecard,
    BuySideAnalysis,
    CommercialSummary,
    ComplianceMatrixSummary,
    CyberPrivacySummary,
    FinancialMetricSummary,
    ForensicSummary,
    LegalStructureSummary,
    ManufacturingMetricsSummary,
    OperationsSummary,
    TaxComplianceSummary,
    TechSaasMetricsSummary,
    VendorRiskTier,
)


def _clip(text: str, limit: int = 220) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 3]}..."


def _tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9]+", text.lower()) if token]


def _score_text(query: str, *texts: str) -> float:
    query = query.strip().lower()
    if not query:
        return 0.0

    haystack = " ".join(texts).lower()
    if not haystack:
        return 0.0

    terms = _tokenize(query)
    if not terms:
        return 0.0

    matches = sum(1 for term in terms if term in haystack)
    phrase_bonus = 1.0 if query in haystack else 0.0
    return (matches / len(terms)) + phrase_bonus


class EvidenceCatalogEntry(BaseModel):
    evidence_id: str
    artifact_id: str | None = None
    title: str
    evidence_kind: str
    citation: str
    excerpt: str
    confidence: float


class ChunkCatalogEntry(BaseModel):
    chunk_id: str
    artifact_id: str
    document_title: str
    document_kind: str
    source_kind: str
    section_title: str | None = None
    page_number: int | None = None
    text: str


class IssueCatalogEntry(BaseModel):
    issue_id: str
    title: str
    severity: str
    status: str
    business_impact: str
    recommended_action: str | None = None


class ChecklistCatalogEntry(BaseModel):
    checklist_id: str
    title: str
    status: str
    detail: str
    mandatory: bool
    owner: str | None = None


class EvidenceSearchArgs(BaseModel):
    query: str = Field(min_length=2, description="Search query over evidence and chunks.")
    top_k: int = Field(default=5, ge=1, le=10, description="Number of results to return.")


class IssueLookupArgs(BaseModel):
    query: str | None = Field(default=None, description="Optional free-text issue filter.")
    severity: str | None = Field(default=None, description="Optional severity filter.")
    status: str | None = Field(default=None, description="Optional status filter.")
    top_k: int = Field(default=5, ge=1, le=10, description="Number of issue rows to return.")


class ChecklistLookupArgs(BaseModel):
    query: str | None = Field(default=None, description="Optional free-text checklist filter.")
    status: str | None = Field(default=None, description="Optional status filter.")
    mandatory_only: bool = Field(
        default=False,
        description="When true, only return mandatory checklist items.",
    )
    top_k: int = Field(default=5, ge=1, le=10, description="Number of checklist rows to return.")


class InstrumentedReadOnlyTool(BaseTool):
    """Base tool that keeps a light usage log for post-run tracing."""

    scope_label: str

    _usage_log: list[dict[str, Any]] = PrivateAttr(default_factory=list)

    def usage_records(self) -> list[dict[str, Any]]:
        return list(self._usage_log)

    def _record_usage(self, *, query: str, result_count: int, preview: str) -> None:
        self._usage_log.append(
            {
                "query": query,
                "result_count": result_count,
                "preview": preview,
            }
        )


class EvidenceSearchTool(InstrumentedReadOnlyTool):
    """Search cited evidence nodes and linked document chunks."""

    name: str = "search_evidence"
    description: str = "Search evidence nodes and linked document chunks."
    args_schema: type[BaseModel] = EvidenceSearchArgs
    evidence_catalog: list[EvidenceCatalogEntry] = Field(default_factory=list, repr=False)
    chunk_catalog: list[ChunkCatalogEntry] = Field(default_factory=list, repr=False)
    default_top_k: int = 5

    def _run(self, query: str, top_k: int = 5) -> str:
        limit = max(1, top_k or self.default_top_k)
        scored: list[tuple[float, str]] = []

        for evidence in self.evidence_catalog:
            score = _score_text(query, evidence.title, evidence.citation, evidence.excerpt)
            if score <= 0:
                continue
            scored.append(
                (
                    score,
                    (
                        f"[Evidence] {evidence.title} | kind={evidence.evidence_kind} | "
                        f"confidence={evidence.confidence:.2f}\n"
                        f"Citation: {evidence.citation}\n"
                        f"Excerpt: {_clip(evidence.excerpt)}"
                    ),
                )
            )

        for chunk in self.chunk_catalog:
            score = _score_text(
                query,
                chunk.document_title,
                chunk.section_title or "",
                chunk.text,
            )
            if score <= 0:
                continue
            location = []
            if chunk.section_title:
                location.append(f"section={chunk.section_title}")
            if chunk.page_number is not None:
                location.append(f"page={chunk.page_number}")
            location_text = ", ".join(location) if location else "section=unspecified"
            scored.append(
                (
                    score,
                    (
                        f"[Chunk] {chunk.document_title} | {location_text} | "
                        f"kind={chunk.document_kind}/{chunk.source_kind}\n"
                        f"Text: {_clip(chunk.text)}"
                    ),
                )
            )

        scored.sort(key=lambda item: item[0], reverse=True)
        results = [payload for _, payload in scored[:limit]]
        if not results:
            message = (
                f"No evidence or document chunks matched '{query}' in the {self.scope_label} scope."
            )
            self._record_usage(query=query, result_count=0, preview=message)
            return message

        preview = results[0].splitlines()[0]
        self._record_usage(query=query, result_count=len(results), preview=preview)
        body = "\n\n".join(f"{index}. {result}" for index, result in enumerate(results, start=1))
        return f"Evidence search results for '{query}' in {self.scope_label}:\n\n{body}"


class IssueRegisterLookupTool(InstrumentedReadOnlyTool):
    """Inspect issues within the current scope."""

    name: str = "review_issues"
    description: str = "Review scoped issue register items."
    args_schema: type[BaseModel] = IssueLookupArgs
    issues: list[IssueCatalogEntry] = Field(default_factory=list, repr=False)
    default_top_k: int = 5

    def _run(
        self,
        query: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        top_k: int = 5,
    ) -> str:
        limit = max(1, top_k or self.default_top_k)
        filtered: list[IssueCatalogEntry] = []
        query_text = query.strip() if query else ""
        severity_filter = severity.strip().lower() if severity else None
        status_filter = status.strip().lower() if status else None

        for issue in self.issues:
            if severity_filter and issue.severity.lower() != severity_filter:
                continue
            if status_filter and issue.status.lower() != status_filter:
                continue
            if (
                query_text
                and _score_text(
                    query_text,
                    issue.title,
                    issue.business_impact,
                    issue.recommended_action or "",
                )
                <= 0
            ):
                continue
            filtered.append(issue)

        if not filtered:
            message = f"No issues matched the requested filters in the {self.scope_label} scope."
            self._record_usage(
                query=query_text or "(filtered lookup)",
                result_count=0,
                preview=message,
            )
            return message

        ordered = sorted(
            filtered,
            key=lambda issue: (
                {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(
                    issue.severity.lower(),
                    5,
                ),
                issue.title.lower(),
            ),
        )[:limit]

        lines = []
        for index, issue in enumerate(ordered, start=1):
            lines.append(
                f"{index}. [{issue.severity}/{issue.status}] {issue.title}\n"
                f"Impact: {_clip(issue.business_impact)}\n"
                f"Action: {_clip(issue.recommended_action or 'Triage pending')}"
            )

        preview = lines[0].splitlines()[0]
        self._record_usage(
            query=query_text or "(filtered lookup)",
            result_count=len(ordered),
            preview=preview,
        )
        return f"Issue register results for {self.scope_label}:\n\n" + "\n\n".join(lines)


class ChecklistGapLookupTool(InstrumentedReadOnlyTool):
    """Inspect checklist gaps within the current scope."""

    name: str = "review_checklist"
    description: str = "Inspect scoped checklist coverage and unresolved gaps."
    args_schema: type[BaseModel] = ChecklistLookupArgs
    checklist_items: list[ChecklistCatalogEntry] = Field(default_factory=list, repr=False)
    default_top_k: int = 5

    def _run(
        self,
        query: str | None = None,
        status: str | None = None,
        mandatory_only: bool = False,
        top_k: int = 5,
    ) -> str:
        limit = max(1, top_k or self.default_top_k)
        query_text = query.strip() if query else ""
        status_filter = status.strip().lower() if status else None
        filtered: list[ChecklistCatalogEntry] = []

        for item in self.checklist_items:
            if mandatory_only and not item.mandatory:
                continue
            if status_filter and item.status.lower() != status_filter:
                continue
            if (
                query_text
                and _score_text(
                    query_text,
                    item.title,
                    item.detail,
                    item.owner or "",
                )
                <= 0
            ):
                continue
            filtered.append(item)

        if not filtered:
            message = (
                f"No checklist items matched the requested filters in the {self.scope_label} scope."
            )
            self._record_usage(
                query=query_text or "(gap lookup)",
                result_count=0,
                preview=message,
            )
            return message

        ordered = sorted(
            filtered,
            key=lambda item: (
                0 if item.mandatory else 1,
                0 if item.status.lower() != "done" else 1,
                item.title.lower(),
            ),
        )[:limit]

        lines = []
        for index, item in enumerate(ordered, start=1):
            mandatory = "mandatory" if item.mandatory else "optional"
            owner = item.owner or "unassigned"
            lines.append(
                f"{index}. [{item.status}] {item.title} ({mandatory}, owner={owner})\n"
                f"Detail: {_clip(item.detail)}"
            )

        preview = lines[0].splitlines()[0]
        self._record_usage(
            query=query_text or "(gap lookup)",
            result_count=len(ordered),
            preview=preview,
        )
        return f"Checklist results for {self.scope_label}:\n\n" + "\n\n".join(lines)


def _build_evidence_catalog(items: list[Any]) -> list[EvidenceCatalogEntry]:
    return [
        EvidenceCatalogEntry(
            evidence_id=item.id,
            artifact_id=getattr(item, "artifact_id", None),
            title=item.title,
            evidence_kind=item.evidence_kind,
            citation=item.citation,
            excerpt=item.excerpt,
            confidence=float(item.confidence),
        )
        for item in items
    ]


def _build_chunk_catalog(items: list[Any]) -> list[ChunkCatalogEntry]:
    return [
        ChunkCatalogEntry(
            chunk_id=item.chunk_id,
            artifact_id=item.artifact_id,
            document_title=item.document_title,
            document_kind=item.document_kind,
            source_kind=item.source_kind,
            section_title=item.section_title,
            page_number=item.page_number,
            text=item.text,
        )
        for item in items
    ]


def _build_issue_catalog(items: list[Any]) -> list[IssueCatalogEntry]:
    return [
        IssueCatalogEntry(
            issue_id=item.id,
            title=item.title,
            severity=item.severity,
            status=item.status,
            business_impact=item.business_impact,
            recommended_action=item.recommended_action,
        )
        for item in items
    ]


def _build_checklist_catalog(items: list[Any]) -> list[ChecklistCatalogEntry]:
    return [
        ChecklistCatalogEntry(
            checklist_id=item.id,
            title=item.title,
            status=item.status,
            detail=item.detail,
            mandatory=bool(item.mandatory),
            owner=item.owner,
        )
        for item in items
    ]


def build_workstream_tools(
    *,
    workstream_domain: str,
    motion_pack: str = "",
    evidence_items: list[Any],
    issues: list[Any],
    checklist_items: list[Any],
    chunk_items: list[Any],
    max_usage_count: int,
    default_top_k: int = 5,
    financial_summary: FinancialMetricSummary | None = None,
    legal_summary: LegalStructureSummary | None = None,
    tax_summary: TaxComplianceSummary | None = None,
    compliance_summary: ComplianceMatrixSummary | None = None,
    commercial_summary: CommercialSummary | None = None,
    operations_summary: OperationsSummary | None = None,
    cyber_summary: CyberPrivacySummary | None = None,
    forensic_summary: ForensicSummary | None = None,
    sector_pack: str = "tech_saas_services",
    buy_side_analysis: BuySideAnalysis | None = None,
    borrower_scorecard: BorrowerScorecard | None = None,
    vendor_risk_tier: VendorRiskTier | None = None,
    tech_saas_metrics: TechSaasMetricsSummary | None = None,
    manufacturing_metrics: ManufacturingMetricsSummary | None = None,
    bfsi_nbfc_metrics: BfsiNbfcMetricsSummary | None = None,
) -> list[BaseTool]:
    scope_label = workstream_domain.replace("_", " ")
    scope_slug = workstream_domain.lower()
    tools: list[Any] = [
        EvidenceSearchTool(
            name=f"search_{scope_slug}_evidence",
            description=(
                f"Search cited evidence nodes and linked document chunks for the "
                f"{scope_label} workstream."
            ),
            scope_label=scope_label,
            evidence_catalog=_build_evidence_catalog(evidence_items),
            chunk_catalog=_build_chunk_catalog(chunk_items),
            default_top_k=default_top_k,
            max_usage_count=max_usage_count,
        ),
        IssueRegisterLookupTool(
            name=f"review_{scope_slug}_issues",
            description=(
                f"Review issue-register items already flagged in the {scope_label} workstream."
            ),
            scope_label=scope_label,
            issues=_build_issue_catalog(issues),
            default_top_k=default_top_k,
            max_usage_count=max_usage_count,
        ),
        ChecklistGapLookupTool(
            name=f"review_{scope_slug}_checklist",
            description=(
                f"Inspect checklist coverage and unresolved gaps in the {scope_label} workstream."
            ),
            scope_label=scope_label,
            checklist_items=_build_checklist_catalog(checklist_items),
            default_top_k=default_top_k,
            max_usage_count=max_usage_count,
        ),
    ]
    if workstream_domain == "financial_qoe":
        tools.extend(
            build_financial_tools(
                financial_summary=financial_summary,
                sector_pack=sector_pack,
            )
        )
    if workstream_domain in {"legal_corporate", "tax", "regulatory"}:
        tools.extend(
            build_compliance_tools(
                legal_summary=legal_summary,
                tax_summary=tax_summary,
                compliance_summary=compliance_summary,
            )
        )
    phase10_tools = build_phase10_tools(
        commercial_summary=commercial_summary,
        operations_summary=operations_summary,
        cyber_summary=cyber_summary,
        forensic_summary=forensic_summary,
    )
    phase10_tool_names_by_workstream = {
        "commercial": {"review_commercial_signals"},
        "operations": {"review_operations_risks"},
        "cyber_privacy": {"review_cyber_controls"},
        "forensic_compliance": {"review_forensic_flags"},
    }
    tools.extend(
        [
            tool
            for tool in phase10_tools
            if tool.name in phase10_tool_names_by_workstream.get(workstream_domain, set())
        ]
    )
    tools.extend(
        build_phase11_tools(
            motion_pack=motion_pack,
            buy_side_analysis=buy_side_analysis,
            borrower_scorecard=borrower_scorecard,
            vendor_risk_tier=vendor_risk_tier,
        )
    )
    tools.extend(
        build_phase12_tools(
            sector_pack=sector_pack,
            tech_saas_metrics=tech_saas_metrics,
            manufacturing_metrics=manufacturing_metrics,
            bfsi_nbfc_metrics=bfsi_nbfc_metrics,
        )
    )
    return tools


def build_case_tools(
    *,
    motion_pack: str = "",
    evidence_items: list[Any],
    issues: list[Any],
    checklist_items: list[Any],
    chunk_items: list[Any],
    max_usage_count: int,
    default_top_k: int = 5,
    financial_summary: FinancialMetricSummary | None = None,
    legal_summary: LegalStructureSummary | None = None,
    tax_summary: TaxComplianceSummary | None = None,
    compliance_summary: ComplianceMatrixSummary | None = None,
    commercial_summary: CommercialSummary | None = None,
    operations_summary: OperationsSummary | None = None,
    cyber_summary: CyberPrivacySummary | None = None,
    forensic_summary: ForensicSummary | None = None,
    sector_pack: str = "tech_saas_services",
    buy_side_analysis: BuySideAnalysis | None = None,
    borrower_scorecard: BorrowerScorecard | None = None,
    vendor_risk_tier: VendorRiskTier | None = None,
    tech_saas_metrics: TechSaasMetricsSummary | None = None,
    manufacturing_metrics: ManufacturingMetricsSummary | None = None,
    bfsi_nbfc_metrics: BfsiNbfcMetricsSummary | None = None,
) -> list[BaseTool]:
    tools: list[Any] = [
        EvidenceSearchTool(
            name="search_case_evidence",
            description="Search evidence nodes and document chunks across the full case.",
            scope_label="full case",
            evidence_catalog=_build_evidence_catalog(evidence_items),
            chunk_catalog=_build_chunk_catalog(chunk_items),
            default_top_k=default_top_k,
            max_usage_count=max_usage_count,
        ),
        IssueRegisterLookupTool(
            name="review_case_issues",
            description="Review issue-register items across the full case.",
            scope_label="full case",
            issues=_build_issue_catalog(issues),
            default_top_k=default_top_k,
            max_usage_count=max_usage_count,
        ),
        ChecklistGapLookupTool(
            name="review_case_checklist",
            description="Inspect checklist coverage and unresolved gaps across the full case.",
            scope_label="full case",
            checklist_items=_build_checklist_catalog(checklist_items),
            default_top_k=default_top_k,
            max_usage_count=max_usage_count,
        ),
    ]
    tools.extend(
        build_financial_tools(
            financial_summary=financial_summary,
            sector_pack=sector_pack,
        )
    )
    tools.extend(
        build_compliance_tools(
            legal_summary=legal_summary,
            tax_summary=tax_summary,
            compliance_summary=compliance_summary,
        )
    )
    tools.extend(
        build_phase10_tools(
            commercial_summary=commercial_summary,
            operations_summary=operations_summary,
            cyber_summary=cyber_summary,
            forensic_summary=forensic_summary,
        )
    )
    tools.extend(
        build_phase11_tools(
            motion_pack=motion_pack,
            buy_side_analysis=buy_side_analysis,
            borrower_scorecard=borrower_scorecard,
            vendor_risk_tier=vendor_risk_tier,
        )
    )
    tools.extend(
        build_phase12_tools(
            sector_pack=sector_pack,
            tech_saas_metrics=tech_saas_metrics,
            manufacturing_metrics=manufacturing_metrics,
            bfsi_nbfc_metrics=bfsi_nbfc_metrics,
        )
    )
    return tools


def summarize_tool_usage(tools: list[BaseTool]) -> str:
    used_fragments: list[str] = []
    for tool in tools:
        usage_count = getattr(tool, "current_usage_count", 0)
        if usage_count <= 0:
            continue
        latest = None
        if hasattr(tool, "usage_records"):
            records = tool.usage_records()
            latest = records[-1] if records else None
        fragment = f"{tool.name} x{usage_count}"
        if latest and latest["query"]:
            fragment += f" (latest: {_clip(str(latest['query']), 40)})"
        used_fragments.append(fragment)

    if not used_fragments:
        return "No tool calls recorded."

    return "; ".join(used_fragments)


def total_tool_calls(tool_map: dict[str, list[BaseTool]]) -> int:
    return sum(
        getattr(tool, "current_usage_count", 0) for tools in tool_map.values() for tool in tools
    )
