from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.domain.models import (
    ChecklistAutoUpdate,
    ChecklistItemStatus,
    ComplianceStatus,
    TaxComplianceItem,
    TaxComplianceSummary,
)
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.services.document_signal_utils import (
    ArtifactTextSnapshot,
    collect_artifact_snapshots,
    score_snapshot_relevance,
)

COMPLETED_CHECKLIST_STATUSES = {
    ChecklistItemStatus.SATISFIED.value,
    ChecklistItemStatus.NOT_APPLICABLE.value,
}

GSTIN_PATTERN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b")

TAX_AREA_KEYWORDS: dict[str, tuple[str, ...]] = {
    "gst": ("gst", "gstin", "reverse charge", "input credit", "e-way bill"),
    "income_tax": ("income tax", "assessment", "tax return", "section 143"),
    "tds_payroll": ("tds", "withholding tax", "pf", "esi", "payroll"),
    "transfer_pricing": ("transfer pricing", "arm's length", "tp study"),
    "deferred_tax": ("deferred tax", "mat credit", "deferred tax asset"),
}

NEGATIVE_PATTERNS = (
    "notice",
    "demand",
    "show cause",
    "unpaid",
    "default",
    "delay",
    "mismatch",
    "exposure",
    "adjustment",
    "shortfall",
)
PARTIAL_PATTERNS = (
    "pending",
    "under reconciliation",
    "under review",
    "under remediation",
)
POSITIVE_PATTERNS = (
    "compliant",
    "returns filed",
    "filed on time",
    "no notice",
    "no demand",
    "current",
    "up to date",
)
FLATTENED_TAX_KEYWORDS = tuple(
    keyword for values in TAX_AREA_KEYWORDS.values() for keyword in values
)
NEGATIVE_OVERRIDES: dict[str, tuple[str, ...]] = {
    "notice": ("no notice",),
    "demand": ("no demand",),
}


class TaxService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)

    async def build_tax_summary(
        self,
        case_id: str,
        *,
        persist_checklist: bool = True,
    ) -> TaxComplianceSummary | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        snapshots = [
            snapshot
            for snapshot in collect_artifact_snapshots(case)
            if score_snapshot_relevance(
                snapshot,
                workstream_domains=("tax", "regulatory", "financial_qoe"),
                keywords=FLATTENED_TAX_KEYWORDS,
                document_kind_keywords=("tax", "gst", "statutory", "payroll"),
            )
            > 0
        ]

        gstins = sorted(
            {
                match
                for snapshot in snapshots
                for match in GSTIN_PATTERN.findall(snapshot.text.upper())
            }
        )
        items = [self._build_tax_item(area, snapshots) for area in TAX_AREA_KEYWORDS]
        flags = self._build_flags(items, gstins)

        summary = TaxComplianceSummary(
            case_id=case_id,
            gstins=gstins,
            items=items,
            flags=flags,
        )
        if persist_checklist:
            summary.checklist_updates = await self._auto_update_checklist(case, summary)
        return summary

    def _build_tax_item(
        self,
        tax_area: str,
        snapshots: list[ArtifactTextSnapshot],
    ) -> TaxComplianceItem:
        keywords = TAX_AREA_KEYWORDS[tax_area]
        matched_snapshots = [
            snapshot
            for snapshot in snapshots
            if any(keyword in snapshot.text.lower() for keyword in keywords)
            or any(keyword in snapshot.title.lower() for keyword in keywords)
            or any(keyword in snapshot.document_kind.lower() for keyword in keywords)
        ]
        if not matched_snapshots:
            return TaxComplianceItem(
                tax_area=tax_area,
                status=ComplianceStatus.UNKNOWN,
                notes="No direct evidence was found for this tax area.",
            )

        joined = "\n".join(snapshot.text.lower() for snapshot in matched_snapshots)
        negative = self._contains_signal(
            joined,
            NEGATIVE_PATTERNS,
            overrides=NEGATIVE_OVERRIDES,
        )
        partial = self._contains_signal(joined, PARTIAL_PATTERNS)
        positive = self._contains_signal(joined, POSITIVE_PATTERNS)
        if negative and partial:
            status = ComplianceStatus.PARTIALLY_COMPLIANT
        elif negative:
            status = ComplianceStatus.NON_COMPLIANT
        elif positive:
            status = ComplianceStatus.COMPLIANT
        else:
            status = ComplianceStatus.UNKNOWN

        note_fragments = [
            f"Matched {len(matched_snapshots)} artifact(s).",
            self._summarize_snapshot(matched_snapshots[0]),
        ]
        return TaxComplianceItem(
            tax_area=tax_area,
            status=status,
            evidence_ids=sorted(
                {
                    evidence_id
                    for snapshot in matched_snapshots
                    for evidence_id in snapshot.evidence_ids
                }
            ),
            notes=" ".join(fragment for fragment in note_fragments if fragment),
        )

    def _build_flags(
        self,
        items: list[TaxComplianceItem],
        gstins: list[str],
    ) -> list[str]:
        flags: list[str] = []
        by_area = {item.tax_area: item for item in items}
        if by_area["gst"].status in {
            ComplianceStatus.NON_COMPLIANT,
            ComplianceStatus.PARTIALLY_COMPLIANT,
        }:
            flags.append(
                "GST compliance signals suggest notices, reconciliation gaps, "
                "or payment exposure."
            )
        if by_area["transfer_pricing"].status != ComplianceStatus.UNKNOWN:
            flags.append(
                "Transfer-pricing evidence detected; confirm arm's-length "
                "support and adjustment history."
            )
        if by_area["tds_payroll"].status in {
            ComplianceStatus.NON_COMPLIANT,
            ComplianceStatus.PARTIALLY_COMPLIANT,
        }:
            flags.append(
                "TDS or payroll statutory signals indicate withholding, PF, "
                "or ESI follow-up is required."
            )
        if by_area["deferred_tax"].status != ComplianceStatus.UNKNOWN:
            flags.append(
                "Deferred-tax or MAT-credit references detected; reconcile "
                "carrying values and recoverability."
            )
        if not gstins:
            flags.append("No GSTIN was detected in uploaded tax materials.")
        return sorted(set(flags))

    async def _auto_update_checklist(
        self,
        case,
        summary: TaxComplianceSummary,
    ) -> list[ChecklistAutoUpdate]:
        known_items = [
            item for item in summary.items if item.status != ComplianceStatus.UNKNOWN
        ]
        condition_map = {
            "tax.notice_register": bool(known_items or summary.gstins),
            "tax.compliance_borrower_status": bool(known_items or summary.gstins),
            "tax.vendor_statutory_profile": bool(known_items or summary.gstins),
        }
        updated: list[ChecklistAutoUpdate] = []
        for item in case.checklist_items:
            template_key = item.template_key or ""
            if not condition_map.get(template_key):
                continue
            if item.status in COMPLETED_CHECKLIST_STATUSES:
                continue
            note = self._build_checklist_note(summary)
            item.status = ChecklistItemStatus.SATISFIED.value
            item.note = note
            updated.append(
                ChecklistAutoUpdate(
                    checklist_id=item.id,
                    template_key=template_key,
                    status=ChecklistItemStatus.SATISFIED,
                    note=note,
                )
            )

        if updated:
            await self.session.commit()
        return updated

    def _build_checklist_note(self, summary: TaxComplianceSummary) -> str:
        known_items = [item for item in summary.items if item.status != ComplianceStatus.UNKNOWN]
        fragments = [
            "Auto-satisfied by Phase 9 Tax engine.",
            f"Tax areas with evidence: {len(known_items)}.",
        ]
        if summary.gstins:
            fragments.append(f"GSTINs detected: {', '.join(summary.gstins[:3])}.")
        flagged = [
            f"{item.tax_area}={item.status.value}"
            for item in known_items[:4]
        ]
        if flagged:
            fragments.append("Statuses: " + ", ".join(flagged) + ".")
        return " ".join(fragments)

    def _summarize_snapshot(self, snapshot: ArtifactTextSnapshot) -> str:
        cleaned = " ".join(snapshot.text.split())
        if len(cleaned) <= 180:
            return cleaned
        return f"{cleaned[:177]}..."

    def _contains_signal(
        self,
        text: str,
        patterns: tuple[str, ...],
        *,
        overrides: dict[str, tuple[str, ...]] | None = None,
    ) -> bool:
        for pattern in patterns:
            if not self._phrase_present(text, pattern):
                continue
            blocked_phrases = (overrides or {}).get(pattern, ())
            if any(self._phrase_present(text, blocked) for blocked in blocked_phrases):
                continue
            if self._is_negated_phrase(text, pattern):
                continue
            return True
        return False

    def _phrase_present(self, text: str, phrase: str) -> bool:
        escaped = re.escape(phrase.strip().lower()).replace(r"\ ", r"\s+")
        return bool(re.search(rf"(?<!\w){escaped}(?!\w)", text))

    def _is_negated_phrase(self, text: str, phrase: str) -> bool:
        token_count = len(phrase.split())
        if token_count != 1:
            return False
        escaped = re.escape(phrase.strip().lower())
        return bool(re.search(rf"\bno(?:\s+\w+){{0,2}}\s+{escaped}\b", text))
