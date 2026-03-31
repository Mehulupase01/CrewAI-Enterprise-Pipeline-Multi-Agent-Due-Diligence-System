from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.domain.models import (
    ChecklistAutoUpdate,
    ChecklistItemStatus,
    FlagSeverity,
    ForensicFlag,
    ForensicFlagType,
    ForensicSummary,
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

FORENSIC_KEYWORDS = (
    "related party",
    "related-party",
    "promoter-linked",
    "group company",
    "common director",
    "same address",
    "round tripping",
    "fund diversion",
    "end-use deviation",
    "revenue recognition",
    "channel stuffing",
    "bill and hold",
    "side letter",
    "litigation",
    "claim",
    "arbitration",
    "connected lending",
    "evergreening",
)

FLAG_PATTERNS: dict[ForensicFlagType, tuple[str, ...]] = {
    ForensicFlagType.RELATED_PARTY: (
        "related party",
        "related-party",
        "group company",
        "common director",
        "same address",
        "promoter-linked",
        "connected lending",
    ),
    ForensicFlagType.ROUND_TRIPPING: (
        "round tripping",
        "round-tripping",
        "fund diversion",
        "end-use deviation",
        "cash routed",
        "evergreening",
    ),
    ForensicFlagType.REVENUE_ANOMALY: (
        "revenue recognition",
        "channel stuffing",
        "bill and hold",
        "side letter",
        "unbilled revenue",
        "same counterparty",
    ),
    ForensicFlagType.LITIGATION: (
        "litigation",
        "arbitration",
        "claim",
        "dispute",
        "legal notice",
    ),
}

FLAG_METADATA: dict[ForensicFlagType, tuple[FlagSeverity, str]] = {
    ForensicFlagType.RELATED_PARTY: (
        FlagSeverity.HIGH,
        "Related-party, promoter-linked, or common-control patterns require governance review.",
    ),
    ForensicFlagType.ROUND_TRIPPING: (
        FlagSeverity.HIGH,
        "Round-tripping or fund-diversion patterns require source-and-use validation.",
    ),
    ForensicFlagType.REVENUE_ANOMALY: (
        FlagSeverity.HIGH,
        "Revenue recognition or commercial anomaly patterns require earnings-quality review.",
    ),
    ForensicFlagType.LITIGATION: (
        FlagSeverity.MEDIUM,
        "Litigation or dispute patterns require contingent-liability assessment.",
    ),
}


class ForensicService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)

    async def build_forensic_summary(
        self,
        case_id: str,
        *,
        persist_checklist: bool = True,
    ) -> ForensicSummary | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        snapshots = self._select_snapshots(collect_artifact_snapshots(case))
        flags = self._detect_flags(snapshots)
        summary = ForensicSummary(case_id=case_id, flags=flags)
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
                workstream_domains=("forensic_compliance", "legal_corporate", "financial_qoe"),
                keywords=FORENSIC_KEYWORDS,
                document_kind_keywords=("forensic", "bank", "related", "integrity", "litigation"),
            )
            > 0
        ]

    def _detect_flags(
        self,
        snapshots: list[ArtifactTextSnapshot],
    ) -> list[ForensicFlag]:
        flags: list[ForensicFlag] = []
        for flag_type, patterns in FLAG_PATTERNS.items():
            matched_snapshots = [
                snapshot
                for snapshot in snapshots
                if any(pattern in snapshot.text.lower() for pattern in patterns)
                or any(pattern in snapshot.title.lower() for pattern in patterns)
                or any(pattern in snapshot.document_kind.lower() for pattern in patterns)
            ]
            if not matched_snapshots:
                continue
            severity, default_description = FLAG_METADATA[flag_type]
            description = self._build_description(default_description, matched_snapshots)
            flags.append(
                ForensicFlag(
                    flag_type=flag_type,
                    severity=severity,
                    description=description,
                    evidence_ids=sorted(
                        {
                            evidence_id
                            for snapshot in matched_snapshots
                            for evidence_id in snapshot.evidence_ids
                        }
                    ),
                )
            )
        return flags

    async def _auto_update_checklist(
        self,
        case,
        summary: ForensicSummary,
    ) -> list[ChecklistAutoUpdate]:
        flag_types = {flag.flag_type for flag in summary.flags}
        condition_map = {
            "forensic.related_party": ForensicFlagType.RELATED_PARTY in flag_types,
            "forensic.end_use_and_fund_flow": ForensicFlagType.ROUND_TRIPPING in flag_types,
            "forensic.third_party_integrity": bool(summary.flags),
            "forensic.procurement_related_party": ForensicFlagType.RELATED_PARTY in flag_types,
            "forensic.connected_lending_and_evergreening": bool(
                {
                    ForensicFlagType.RELATED_PARTY,
                    ForensicFlagType.ROUND_TRIPPING,
                }.intersection(flag_types)
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

    def _build_checklist_note(self, summary: ForensicSummary) -> str:
        fragments = [
            "Auto-satisfied by Phase 10 Forensic engine.",
            f"Forensic flags: {len(summary.flags)}.",
        ]
        if summary.flags:
            fragments.append(
                "Flag types: " + ", ".join(flag.flag_type.value for flag in summary.flags) + "."
            )
        return " ".join(fragments)

    def _build_description(
        self,
        default_description: str,
        matched_snapshots: list[ArtifactTextSnapshot],
    ) -> str:
        if not matched_snapshots:
            return default_description
        first = matched_snapshots[0]
        cleaned = " ".join(first.text.split())
        excerpt = cleaned[:220] + ("..." if len(cleaned) > 220 else "")
        return f"{default_description} Evidence: {excerpt}"
