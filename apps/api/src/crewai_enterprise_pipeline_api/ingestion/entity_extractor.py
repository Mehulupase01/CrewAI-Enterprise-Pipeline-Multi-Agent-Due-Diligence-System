"""Rule-based entity extractor per document kind.

Scans parsed text for structured data patterns (financials, legal entities,
regulatory identifiers) and returns ``EvidenceItemCreate`` instances that
the ingestion service can persist.
"""

from __future__ import annotations

import re

from crewai_enterprise_pipeline_api.domain.models import (
    EvidenceItemCreate,
    EvidenceKind,
    WorkstreamDomain,
)

# ---------------------------------------------------------------------------
# Financial patterns
# ---------------------------------------------------------------------------

_INR_AMOUNT_RE = re.compile(
    r"(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*"
    r"(?:crore|cr|lakh|lakhs|mn|million|billion|bn|thousand)?",
    re.IGNORECASE,
)

_REVENUE_RE = re.compile(
    r"(?:revenue|turnover|total\s+income|net\s+sales)"
    r"[\w\s:\-]{0,20}?(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*"
    r"(?:crore|cr|lakh|lakhs|mn|million)?",
    re.IGNORECASE,
)

_EBITDA_RE = re.compile(
    r"EBITDA[\w\s:\-]{0,20}?(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*"
    r"(?:crore|cr|lakh|lakhs|mn|million)?",
    re.IGNORECASE,
)

_PAT_RE = re.compile(
    r"(?:PAT|profit\s+after\s+tax|net\s+profit)"
    r"[\w\s:\-]{0,20}?(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*"
    r"(?:crore|cr|lakh|lakhs|mn|million)?",
    re.IGNORECASE,
)

_NET_DEBT_RE = re.compile(
    r"(?:net\s+debt|total\s+debt|total\s+borrowings)"
    r"[\w\s:\-]{0,20}?(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*"
    r"(?:crore|cr|lakh|lakhs|mn|million)?",
    re.IGNORECASE,
)

_AUDITOR_RE = re.compile(
    r"(?:statutory\s+auditor|audited\s+by|auditor)[:\s\-]*([A-Z][\w\s&.,]+)",
    re.IGNORECASE,
)

_AUDIT_OPINION_RE = re.compile(
    r"(?:unqualified|qualified|adverse|disclaimer\s+of)\s*(?:opinion)?",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Legal patterns
# ---------------------------------------------------------------------------

_PARTY_RE = re.compile(
    r"(?:between|party|parties)[:\s\-]*([A-Z][\w\s&.,]+?)(?:\s+and\s+|\s*[,;])",
    re.IGNORECASE,
)

_EXECUTION_DATE_RE = re.compile(
    r"(?:dated|executed\s+on|effective\s+date)[:\s\-]*"
    r"(\d{1,2}[\s/\-]\w+[\s/\-]\d{4}|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)

_GOVERNING_LAW_RE = re.compile(
    r"(?:governed\s+by|governing\s+law|jurisdiction)[:\s\-]*([\w\s]+?(?:law|act|jurisdiction))",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Regulatory patterns
# ---------------------------------------------------------------------------

_CIN_RE = re.compile(r"\b([A-Z]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})\b")

_GSTIN_RE = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d][A-Z\d])\b")

_REG_NUMBER_RE = re.compile(
    r"(?:registration\s*(?:no|number|#)|license\s*(?:no|number))"
    r"[:\s\-]*([A-Z0-9\-/]+)",
    re.IGNORECASE,
)

_VALIDITY_DATE_RE = re.compile(
    r"(?:valid\s+(?:till|until|upto)|expir(?:y|es)\s+(?:on|date))"
    r"[:\s\-]*(\d{1,2}[\s/\-]\w+[\s/\-]\d{4}|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)


def extract_entities(
    text: str,
    document_kind: str,
    artifact_id: str,
    citation_prefix: str,
) -> list[EvidenceItemCreate]:
    """Extract structured entities from *text* based on *document_kind*.

    Returns a list of ``EvidenceItemCreate`` instances ready for persistence.
    """
    lower_kind = document_kind.lower()
    entities: list[EvidenceItemCreate] = []

    if any(k in lower_kind for k in ("financial", "p&l", "balance", "audit", "annual")):
        entities.extend(_extract_financial(text, artifact_id, citation_prefix))

    if any(k in lower_kind for k in ("legal", "contract", "agreement", "deed")):
        entities.extend(_extract_legal(text, artifact_id, citation_prefix))

    if any(k in lower_kind for k in ("regulatory", "license", "registration", "compliance")):
        entities.extend(_extract_regulatory(text, artifact_id, citation_prefix))

    # Always scan for CIN/GSTIN regardless of document_kind
    entities.extend(_extract_india_identifiers(text, artifact_id, citation_prefix))

    return entities


def _make_evidence(
    title: str,
    excerpt: str,
    kind: EvidenceKind,
    domain: WorkstreamDomain,
    artifact_id: str,
    citation: str,
    confidence: float = 0.8,
) -> EvidenceItemCreate:
    return EvidenceItemCreate(
        title=title,
        evidence_kind=kind,
        workstream_domain=domain,
        citation=citation,
        excerpt=excerpt,
        artifact_id=artifact_id,
        confidence=confidence,
    )


def _extract_financial(
    text: str,
    artifact_id: str,
    citation_prefix: str,
) -> list[EvidenceItemCreate]:
    results: list[EvidenceItemCreate] = []

    for match in _REVENUE_RE.finditer(text):
        results.append(
            _make_evidence(
                title="Revenue / Turnover",
                excerpt=match.group(0).strip(),
                kind=EvidenceKind.METRIC,
                domain=WorkstreamDomain.FINANCIAL_QOE,
                artifact_id=artifact_id,
                citation=f"{citation_prefix} :: revenue",
            )
        )

    for match in _EBITDA_RE.finditer(text):
        results.append(
            _make_evidence(
                title="EBITDA",
                excerpt=match.group(0).strip(),
                kind=EvidenceKind.METRIC,
                domain=WorkstreamDomain.FINANCIAL_QOE,
                artifact_id=artifact_id,
                citation=f"{citation_prefix} :: ebitda",
            )
        )

    for match in _PAT_RE.finditer(text):
        results.append(
            _make_evidence(
                title="Profit After Tax",
                excerpt=match.group(0).strip(),
                kind=EvidenceKind.METRIC,
                domain=WorkstreamDomain.FINANCIAL_QOE,
                artifact_id=artifact_id,
                citation=f"{citation_prefix} :: pat",
            )
        )

    for match in _NET_DEBT_RE.finditer(text):
        results.append(
            _make_evidence(
                title="Net Debt / Borrowings",
                excerpt=match.group(0).strip(),
                kind=EvidenceKind.METRIC,
                domain=WorkstreamDomain.FINANCIAL_QOE,
                artifact_id=artifact_id,
                citation=f"{citation_prefix} :: debt",
            )
        )

    for match in _AUDITOR_RE.finditer(text):
        results.append(
            _make_evidence(
                title="Statutory Auditor",
                excerpt=match.group(0).strip(),
                kind=EvidenceKind.FACT,
                domain=WorkstreamDomain.FINANCIAL_QOE,
                artifact_id=artifact_id,
                citation=f"{citation_prefix} :: auditor",
                confidence=0.85,
            )
        )

    for match in _AUDIT_OPINION_RE.finditer(text):
        results.append(
            _make_evidence(
                title="Audit Opinion",
                excerpt=match.group(0).strip(),
                kind=EvidenceKind.FACT,
                domain=WorkstreamDomain.FINANCIAL_QOE,
                artifact_id=artifact_id,
                citation=f"{citation_prefix} :: audit-opinion",
                confidence=0.9,
            )
        )

    return results


def _extract_legal(
    text: str,
    artifact_id: str,
    citation_prefix: str,
) -> list[EvidenceItemCreate]:
    results: list[EvidenceItemCreate] = []

    for match in _PARTY_RE.finditer(text):
        results.append(
            _make_evidence(
                title="Contract Party",
                excerpt=match.group(0).strip(),
                kind=EvidenceKind.CONTRACT,
                domain=WorkstreamDomain.LEGAL_CORPORATE,
                artifact_id=artifact_id,
                citation=f"{citation_prefix} :: party",
            )
        )

    for match in _EXECUTION_DATE_RE.finditer(text):
        results.append(
            _make_evidence(
                title="Execution Date",
                excerpt=match.group(0).strip(),
                kind=EvidenceKind.FACT,
                domain=WorkstreamDomain.LEGAL_CORPORATE,
                artifact_id=artifact_id,
                citation=f"{citation_prefix} :: execution-date",
            )
        )

    for match in _GOVERNING_LAW_RE.finditer(text):
        results.append(
            _make_evidence(
                title="Governing Law",
                excerpt=match.group(0).strip(),
                kind=EvidenceKind.GOVERNANCE,
                domain=WorkstreamDomain.LEGAL_CORPORATE,
                artifact_id=artifact_id,
                citation=f"{citation_prefix} :: governing-law",
            )
        )

    return results


def _extract_regulatory(
    text: str,
    artifact_id: str,
    citation_prefix: str,
) -> list[EvidenceItemCreate]:
    results: list[EvidenceItemCreate] = []

    for match in _REG_NUMBER_RE.finditer(text):
        results.append(
            _make_evidence(
                title="Registration / License Number",
                excerpt=match.group(0).strip(),
                kind=EvidenceKind.FACT,
                domain=WorkstreamDomain.REGULATORY,
                artifact_id=artifact_id,
                citation=f"{citation_prefix} :: reg-number",
            )
        )

    for match in _VALIDITY_DATE_RE.finditer(text):
        results.append(
            _make_evidence(
                title="License Validity Date",
                excerpt=match.group(0).strip(),
                kind=EvidenceKind.FACT,
                domain=WorkstreamDomain.REGULATORY,
                artifact_id=artifact_id,
                citation=f"{citation_prefix} :: validity-date",
            )
        )

    return results


def _extract_india_identifiers(
    text: str,
    artifact_id: str,
    citation_prefix: str,
) -> list[EvidenceItemCreate]:
    results: list[EvidenceItemCreate] = []
    seen: set[str] = set()

    for match in _CIN_RE.finditer(text):
        cin = match.group(1)
        if cin not in seen:
            seen.add(cin)
            results.append(
                _make_evidence(
                    title=f"CIN: {cin}",
                    excerpt=f"Corporate Identity Number: {cin}",
                    kind=EvidenceKind.FACT,
                    domain=WorkstreamDomain.LEGAL_CORPORATE,
                    artifact_id=artifact_id,
                    citation=f"{citation_prefix} :: cin",
                    confidence=0.95,
                )
            )

    for match in _GSTIN_RE.finditer(text):
        gstin = match.group(1)
        if gstin not in seen:
            seen.add(gstin)
            results.append(
                _make_evidence(
                    title=f"GSTIN: {gstin}",
                    excerpt=f"GST Identification Number: {gstin}",
                    kind=EvidenceKind.FACT,
                    domain=WorkstreamDomain.TAX,
                    artifact_id=artifact_id,
                    citation=f"{citation_prefix} :: gstin",
                    confidence=0.95,
                )
            )

    return results
