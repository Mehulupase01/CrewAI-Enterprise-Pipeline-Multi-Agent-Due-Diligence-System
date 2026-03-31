from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.domain.models import (
    ChecklistAutoUpdate,
    ChecklistItemStatus,
    OperationsDependencySignal,
    OperationsSummary,
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

OPERATIONS_KEYWORDS = (
    "supply chain",
    "supplier",
    "raw material",
    "plant",
    "facility",
    "capacity",
    "downtime",
    "maintenance",
    "continuity",
    "outsourcing",
    "key person",
    "key-man",
    "founder dependent",
    "single site",
    "single plant",
    "single cloud provider",
    "underwriting",
    "collections",
)

SUPPLIER_CONCENTRATION_PATTERN = re.compile(
    r"(?:(?:top\s*\d+\s+suppliers?)|supplier concentration|single supplier|sole supplier)"
    r"[^0-9]{0,35}(?P<pct>\d{1,3}(?:\.\d+)?)\s*(?:%|percent)",
    re.IGNORECASE,
)
SUPPLY_CHAIN_KEYWORDS = (
    "supplier concentration",
    "single supplier",
    "sole supplier",
    "raw material shortage",
    "import dependency",
)
KEY_PERSON_KEYWORDS = (
    "key-man",
    "key man",
    "key-person",
    "key person",
    "founder dependent",
    "single engineer",
    "single architect",
    "single plant head",
)
CONTINUITY_KEYWORDS = (
    "single site",
    "single plant",
    "single facility",
    "single warehouse",
    "no disaster recovery",
    "no redundancy",
    "single cloud provider",
    "outsourcing dependency",
    "business continuity gap",
    "manual fallback unavailable",
)
CAPACITY_KEYWORDS = ("capacity", "utilisation", "utilization", "downtime", "maintenance")
BFSI_OPERATIONS_KEYWORDS = (
    "underwriting override",
    "collections governance",
    "collection agency",
    "grievance escalation",
    "lsp dependency",
)


class OperationsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)

    async def build_operations_summary(
        self,
        case_id: str,
        *,
        persist_checklist: bool = True,
    ) -> OperationsSummary | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        snapshots = self._select_snapshots(collect_artifact_snapshots(case))
        supplier_concentration_top_3 = self._extract_supplier_concentration(snapshots)
        dependency_signals = self._extract_dependency_signals(snapshots)
        single_site_dependency = any(
            signal.dependency_type == "site" for signal in dependency_signals
        )
        key_person_dependencies = [
            signal.detail
            for signal in dependency_signals
            if signal.dependency_type == "key_person"
        ][:5]
        flags = self._build_flags(
            supplier_concentration_top_3,
            dependency_signals,
            single_site_dependency,
            key_person_dependencies,
        )

        summary = OperationsSummary(
            case_id=case_id,
            supplier_concentration_top_3=supplier_concentration_top_3,
            dependency_signals=dependency_signals,
            single_site_dependency=single_site_dependency,
            key_person_dependencies=key_person_dependencies,
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
                workstream_domains=("operations", "commercial", "cyber_privacy"),
                keywords=OPERATIONS_KEYWORDS,
                document_kind_keywords=(
                    "operations",
                    "manufacturing",
                    "continuity",
                    "supplier",
                    "collections",
                ),
            )
            > 0
        ]

    def _extract_supplier_concentration(
        self,
        snapshots: list[ArtifactTextSnapshot],
    ) -> float | None:
        values: list[float] = []
        for snapshot in snapshots:
            normalized = snapshot.text.replace(" percent", "%").replace(" Percent", "%")
            for match in SUPPLIER_CONCENTRATION_PATTERN.finditer(normalized):
                values.append(round(min(float(match.group("pct")) / 100.0, 1.0), 4))
        if not values:
            return None
        return max(values)

    def _extract_dependency_signals(
        self,
        snapshots: list[ArtifactTextSnapshot],
    ) -> list[OperationsDependencySignal]:
        signals: list[OperationsDependencySignal] = []
        seen: set[tuple[str, str]] = set()
        for snapshot in snapshots:
            for sentence in self._sentences(snapshot.text):
                lowered = sentence.lower()
                dependency_type = None
                label = None
                if any(keyword in lowered for keyword in SUPPLY_CHAIN_KEYWORDS):
                    dependency_type = "supply_chain"
                    label = "Supply-chain concentration or raw-material dependency"
                elif any(keyword in lowered for keyword in KEY_PERSON_KEYWORDS):
                    dependency_type = "key_person"
                    label = "Key-person dependency"
                elif any(keyword in lowered for keyword in CONTINUITY_KEYWORDS):
                    dependency_type = "site"
                    label = "Single-site or continuity dependency"
                elif any(keyword in lowered for keyword in CAPACITY_KEYWORDS):
                    dependency_type = "capacity"
                    label = "Capacity, downtime, or maintenance signal"
                elif any(keyword in lowered for keyword in BFSI_OPERATIONS_KEYWORDS):
                    dependency_type = "governance"
                    label = "Underwriting or collections governance dependency"

                if dependency_type is None or label is None:
                    continue

                cleaned = " ".join(sentence.split())
                key = (dependency_type, cleaned)
                if key in seen:
                    continue
                seen.add(key)
                signals.append(
                    OperationsDependencySignal(
                        dependency_type=dependency_type,
                        label=label,
                        detail=cleaned,
                        evidence_ids=sorted(snapshot.evidence_ids),
                    )
                )
        return signals[:10]

    def _build_flags(
        self,
        supplier_concentration_top_3: float | None,
        dependency_signals: list[OperationsDependencySignal],
        single_site_dependency: bool,
        key_person_dependencies: list[str],
    ) -> list[str]:
        flags: list[str] = []
        if supplier_concentration_top_3 is not None and supplier_concentration_top_3 >= 0.50:
            flags.append(
                f"Supplier concentration is elevated at {supplier_concentration_top_3:.0%}."
            )
        if single_site_dependency:
            flags.append(
                "Single-site or continuity dependency signals were detected in "
                "operational materials."
            )
        if key_person_dependencies:
            flags.append("Key-person dependency signals were detected in operational materials.")
        if any(signal.dependency_type == "capacity" for signal in dependency_signals):
            flags.append("Capacity, downtime, or maintenance signals require operations follow-up.")
        if any(signal.dependency_type == "governance" for signal in dependency_signals):
            flags.append(
                "Underwriting or collections governance dependencies require operational review."
            )
        return flags

    async def _auto_update_checklist(
        self,
        case,
        summary: OperationsSummary,
    ) -> list[ChecklistAutoUpdate]:
        has_signals = bool(
            summary.dependency_signals
            or summary.supplier_concentration_top_3 is not None
            or summary.key_person_dependencies
        )
        condition_map = {
            "operations.service_continuity": has_signals,
            "operations.delivery_model": has_signals,
            "operations.plant_capacity_utilisation": bool(
                summary.single_site_dependency
                or any(
                    signal.dependency_type == "capacity"
                    for signal in summary.dependency_signals
                )
            ),
            "operations.supplier_concentration": bool(
                summary.supplier_concentration_top_3 is not None
                or any(
                    signal.dependency_type == "supply_chain"
                    for signal in summary.dependency_signals
                )
            ),
            "operations.underwriting_and_collections_governance": any(
                signal.dependency_type == "governance"
                for signal in summary.dependency_signals
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

    def _build_checklist_note(self, summary: OperationsSummary) -> str:
        fragments = [
            "Auto-satisfied by Phase 10 Operations engine.",
            f"Dependency signals: {len(summary.dependency_signals)}.",
        ]
        if summary.supplier_concentration_top_3 is not None:
            fragments.append(
                f"Supplier concentration: {summary.supplier_concentration_top_3:.0%}."
            )
        if summary.key_person_dependencies:
            fragments.append(f"Key-person signals: {len(summary.key_person_dependencies)}.")
        return " ".join(fragments)

    def _sentences(self, text: str) -> list[str]:
        return [
            segment.strip()
            for segment in re.split(r"(?<=[.!?])\s+|\n+", text)
            if segment.strip()
        ]
