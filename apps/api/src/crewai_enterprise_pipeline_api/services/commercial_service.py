from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.domain.models import (
    ChecklistAutoUpdate,
    ChecklistItemStatus,
    CommercialConcentrationSignal,
    CommercialRenewalSignal,
    CommercialSummary,
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

COMMERCIAL_KEYWORDS = (
    "customer",
    "arr",
    "revenue retention",
    "nrr",
    "churn",
    "renewal",
    "pricing",
    "discount",
    "dealer",
    "distributor",
    "order book",
)

CONCENTRATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?P<label>top\s*\d+\s+(?:customers?|dealers?|distributors?)|single customer|single "
        r"dealer|single distributor|one top customer|top customer|customer concentration|"
        r"dealer concentration|channel concentration|distributor concentration)"
        r"[^0-9]{0,40}(?P<pct>\d{1,3}(?:\.\d+)?)\s*(?:%|percent)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<label>[A-Z][A-Za-z0-9&().,\- ]{2,40})[^.\n]{0,40}"
        r"(?:contributes|accounts for)[^0-9]{0,20}(?P<pct>\d{1,3}(?:\.\d+)?)\s*"
        r"(?:%|percent)[^.\n]{0,30}(?:of revenue|of arr|of sales|of collections)",
        re.IGNORECASE,
    ),
)
NRR_PATTERN = re.compile(
    r"(?:net revenue retention|nrr)[^0-9]{0,20}(?P<value>\d{1,3}(?:\.\d+)?)\s*(?:%|percent)?",
    re.IGNORECASE,
)
CHURN_PATTERN = re.compile(
    r"(?:gross churn|net churn|customer churn|churn)[^0-9]{0,20}(?P<value>\d{1,3}(?:\.\d+)?)"
    r"\s*(?:%|percent)",
    re.IGNORECASE,
)
PRICING_KEYWORDS = (
    "pricing pressure",
    "price erosion",
    "discounting",
    "discount pressure",
    "price cut",
    "pricing concession",
    "discount requested",
)
RENEWAL_KEYWORDS = ("renewal", "renew", "termination", "auto-renew")


class CommercialService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)

    async def build_commercial_summary(
        self,
        case_id: str,
        *,
        persist_checklist: bool = True,
    ) -> CommercialSummary | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        snapshots = self._select_snapshots(collect_artifact_snapshots(case))
        concentration_signals = self._extract_concentration_signals(snapshots)
        net_revenue_retention = self._extract_ratio_metric(snapshots, NRR_PATTERN)
        churn_rate = self._extract_ratio_metric(snapshots, CHURN_PATTERN)
        pricing_signals = self._extract_sentence_signals(snapshots, PRICING_KEYWORDS)
        renewal_signals = self._extract_renewal_signals(snapshots)
        flags = self._build_flags(
            concentration_signals,
            net_revenue_retention,
            churn_rate,
            pricing_signals,
            renewal_signals,
        )

        summary = CommercialSummary(
            case_id=case_id,
            concentration_signals=concentration_signals,
            net_revenue_retention=net_revenue_retention,
            churn_rate=churn_rate,
            pricing_signals=pricing_signals,
            renewal_signals=renewal_signals,
            flags=flags,
        )
        if persist_checklist:
            summary.checklist_updates = await self._auto_update_checklist(case, summary)
        return summary

    def _select_snapshots(
        self,
        snapshots: list[ArtifactTextSnapshot],
    ) -> list[ArtifactTextSnapshot]:
        return [
            snapshot
            for snapshot in snapshots
            if score_snapshot_relevance(
                snapshot,
                workstream_domains=("commercial", "financial_qoe"),
                keywords=COMMERCIAL_KEYWORDS,
                document_kind_keywords=("commercial", "arr", "sales", "customer", "renewal"),
            )
            > 0
        ]

    def _extract_concentration_signals(
        self,
        snapshots: list[ArtifactTextSnapshot],
    ) -> list[CommercialConcentrationSignal]:
        signals: dict[tuple[str, float], CommercialConcentrationSignal] = {}
        for snapshot in snapshots:
            normalized = snapshot.text.replace(" percent", "%").replace(" Percent", "%")
            for pattern in CONCENTRATION_PATTERNS:
                for match in pattern.finditer(normalized):
                    label = re.sub(r"\s+", " ", match.group("label")).strip(" .,:;|-")
                    share = round(min(float(match.group("pct")) / 100.0, 1.0), 4)
                    if share <= 0:
                        continue
                    key = (label.lower(), share)
                    note = self._excerpt_around(normalized, match.start(), match.end())
                    if key not in signals:
                        signals[key] = CommercialConcentrationSignal(
                            subject=label,
                            share_of_revenue=share,
                            category="customer",
                            note=note,
                            evidence_ids=sorted(snapshot.evidence_ids),
                        )
        return sorted(
            signals.values(),
            key=lambda item: (-item.share_of_revenue, item.subject.lower()),
        )

    def _extract_ratio_metric(
        self,
        snapshots: list[ArtifactTextSnapshot],
        pattern: re.Pattern[str],
    ) -> float | None:
        values: list[float] = []
        for snapshot in snapshots:
            for match in pattern.finditer(snapshot.text):
                value = float(match.group("value"))
                if value > 3:
                    value = value / 100.0
                values.append(round(value, 4))
        if not values:
            return None
        return values[-1]

    def _extract_sentence_signals(
        self,
        snapshots: list[ArtifactTextSnapshot],
        keywords: tuple[str, ...],
    ) -> list[str]:
        signals: list[str] = []
        for snapshot in snapshots:
            for sentence in self._sentences(snapshot.text):
                lowered = sentence.lower()
                if any(keyword in lowered for keyword in keywords):
                    cleaned = " ".join(sentence.split())
                    if cleaned not in signals:
                        signals.append(cleaned)
        return signals[:6]

    def _extract_renewal_signals(
        self,
        snapshots: list[ArtifactTextSnapshot],
    ) -> list[CommercialRenewalSignal]:
        results: list[CommercialRenewalSignal] = []
        seen: set[tuple[str, str]] = set()
        for snapshot in snapshots:
            for sentence in self._sentences(snapshot.text):
                lowered = sentence.lower()
                if not any(keyword in lowered for keyword in RENEWAL_KEYWORDS):
                    continue
                status = "monitor"
                if any(
                    token in lowered for token in ("at risk", "termination", "non-renew", "churn")
                ):
                    status = "at_risk"
                elif any(
                    token in lowered
                    for token in ("next quarter", "next month", "up for renewal", "renewal due")
                ):
                    status = "due_soon"
                elif any(token in lowered for token in ("renewed", "extended", "auto-renewed")):
                    status = "renewed"
                counterparty = self._extract_counterparty(sentence)
                cleaned = " ".join(sentence.split())
                key = (status, cleaned)
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    CommercialRenewalSignal(
                        counterparty=counterparty,
                        status=status,
                        note=cleaned,
                        evidence_ids=sorted(snapshot.evidence_ids),
                    )
                )
        return results[:8]

    def _build_flags(
        self,
        concentration_signals: list[CommercialConcentrationSignal],
        net_revenue_retention: float | None,
        churn_rate: float | None,
        pricing_signals: list[str],
        renewal_signals: list[CommercialRenewalSignal],
    ) -> list[str]:
        flags: list[str] = []
        if concentration_signals:
            top_signal = concentration_signals[0]
            if top_signal.share_of_revenue >= 0.60:
                flags.append(
                    f"Customer concentration is elevated: {top_signal.subject} accounts for "
                    f"{top_signal.share_of_revenue:.0%} of revenue."
                )
            elif top_signal.share_of_revenue >= 0.35:
                flags.append(
                    f"Commercial concentration needs monitoring: {top_signal.subject} accounts for "
                    f"{top_signal.share_of_revenue:.0%} of revenue."
                )
        if net_revenue_retention is not None and net_revenue_retention < 1.0:
            flags.append(f"Net revenue retention is below 100% at {net_revenue_retention:.0%}.")
        if churn_rate is not None and churn_rate >= 0.10:
            flags.append(f"Customer churn is elevated at {churn_rate:.0%}.")
        if pricing_signals:
            flags.append(
                "Pricing pressure or discounting signals were detected in commercial materials."
            )
        if any(signal.status == "at_risk" for signal in renewal_signals):
            flags.append("At-risk renewal language was detected in customer or channel materials.")
        elif any(signal.status == "due_soon" for signal in renewal_signals):
            flags.append(
                "Material renewal timing should be monitored in the next reporting window."
            )
        return flags

    async def _auto_update_checklist(
        self,
        case,
        summary: CommercialSummary,
    ) -> list[ChecklistAutoUpdate]:
        has_signals = bool(
            summary.concentration_signals
            or summary.net_revenue_retention is not None
            or summary.churn_rate is not None
            or summary.renewal_signals
            or summary.pricing_signals
        )
        condition_map = {
            "commercial.customer_concentration": has_signals,
            "commercial.counterparty_concentration": bool(summary.concentration_signals),
            "commercial.orderbook_channel_mix": bool(
                summary.concentration_signals or summary.renewal_signals
            ),
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

    def _build_checklist_note(self, summary: CommercialSummary) -> str:
        fragments = [
            "Auto-satisfied by Phase 10 Commercial engine.",
            f"Concentration signals: {len(summary.concentration_signals)}.",
            f"Renewal signals: {len(summary.renewal_signals)}.",
        ]
        if summary.concentration_signals:
            top_signal = summary.concentration_signals[0]
            fragments.append(
                f"Top concentration: {top_signal.subject} at {top_signal.share_of_revenue:.0%}."
            )
        if summary.net_revenue_retention is not None:
            fragments.append(f"NRR: {summary.net_revenue_retention:.0%}.")
        if summary.churn_rate is not None:
            fragments.append(f"Churn: {summary.churn_rate:.0%}.")
        return " ".join(fragments)

    def _extract_counterparty(self, sentence: str) -> str | None:
        match = re.search(
            r"\b([A-Z][A-Za-z0-9&().,\- ]{2,40})\b[^.]{0,25}(?:renewal|renewed|termination)",
            sentence,
        )
        if match is None:
            return None
        return re.sub(r"\s+", " ", match.group(1)).strip(" .,:;|-")

    def _sentences(self, text: str) -> list[str]:
        return [
            segment.strip() for segment in re.split(r"(?<=[.!?])\s+|\n+", text) if segment.strip()
        ]

    def _excerpt_around(self, text: str, start: int, end: int) -> str:
        snippet_start = max(0, start - 80)
        snippet_end = min(len(text), end + 120)
        return " ".join(text[snippet_start:snippet_end].split())
