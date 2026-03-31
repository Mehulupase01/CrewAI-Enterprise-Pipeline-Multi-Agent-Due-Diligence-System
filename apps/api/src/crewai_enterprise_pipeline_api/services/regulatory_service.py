from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.domain.models import (
    ChecklistAutoUpdate,
    ChecklistItemStatus,
    ComplianceMatrixItem,
    ComplianceMatrixSummary,
    ComplianceStatus,
    SectorPack,
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


@dataclass(frozen=True)
class RegulationDefinition:
    regulation: str
    regulator: str
    keywords: tuple[str, ...]
    positive_patterns: tuple[str, ...]
    negative_patterns: tuple[str, ...]
    partial_patterns: tuple[str, ...] = ()


COMMON_REGULATIONS: tuple[RegulationDefinition, ...] = (
    RegulationDefinition(
        regulation="MCA Statutory Filings",
        regulator="Ministry of Corporate Affairs",
        keywords=("mca", "din", "aoc-4", "mgt-7", "annual return", "charge"),
        positive_patterns=("filed", "active", "current", "valid"),
        negative_patterns=("mismatch", "overdue", "struck off", "disqualified"),
        partial_patterns=("pending", "under remediation", "under review"),
    ),
    RegulationDefinition(
        regulation="Licensing / Registration Restrictions",
        regulator="Sectoral / State Authorities",
        keywords=("licence", "license", "registration", "permit", "sanctions", "watchlist"),
        positive_patterns=("current", "valid", "active", "no sanctions"),
        negative_patterns=("cancelled", "expired", "sanctions", "watchlist hit"),
        partial_patterns=("renewal pending", "under renewal", "pending"),
    ),
)

SECTOR_REGULATIONS: dict[str, tuple[RegulationDefinition, ...]] = {
    SectorPack.TECH_SAAS_SERVICES.value: (
        RegulationDefinition(
            regulation="DPDP 2025 Readiness",
            regulator="MeitY / DPB",
            keywords=("dpdp", "consent", "privacy", "data fiduciary", "breach notification"),
            positive_patterns=("compliant", "implemented", "current", "completed"),
            negative_patterns=("breach", "non-compliant", "missing consent", "data leak"),
            partial_patterns=("gap", "under remediation", "in progress"),
        ),
        RegulationDefinition(
            regulation="IT Act / Data Localization",
            regulator="MeitY",
            keywords=("it act", "data localization", "cross-border", "intermediary"),
            positive_patterns=("aligned", "compliant", "approved"),
            negative_patterns=("violation", "non-compliant", "breach"),
            partial_patterns=("pending", "under review"),
        ),
    ),
    SectorPack.MANUFACTURING_INDUSTRIALS.value: (
        RegulationDefinition(
            regulation="Factory Licence",
            regulator="Factory Inspectorate",
            keywords=("factory licence", "factory license", "factory licence renewal"),
            positive_patterns=("valid", "current", "renewed"),
            negative_patterns=("expired", "cancelled", "lapsed"),
            partial_patterns=("pending", "renewal pending", "under renewal"),
        ),
        RegulationDefinition(
            regulation="Environmental / PCB Consent",
            regulator="Pollution Control Board",
            keywords=("consent to operate", "pcb", "pollution control", "environmental clearance"),
            positive_patterns=("valid", "current", "approved"),
            negative_patterns=("notice", "violation", "expired", "denied"),
            partial_patterns=("pending", "renewal pending", "under remediation"),
        ),
    ),
    SectorPack.BFSI_NBFC.value: (
        RegulationDefinition(
            regulation="RBI NBFC Registration",
            regulator="Reserve Bank of India",
            keywords=("rbi", "certificate of registration", "nbfc", "registration"),
            positive_patterns=("current", "valid", "compliant", "registered"),
            negative_patterns=("cancelled", "revoked", "supervisory action", "breach"),
            partial_patterns=("remediation", "conditional", "pending"),
        ),
        RegulationDefinition(
            regulation="RBI / Prudential Returns",
            regulator="Reserve Bank of India",
            keywords=("crar", "npa", "prudential", "returns", "supervisory"),
            positive_patterns=("filed", "within threshold", "current"),
            negative_patterns=("breach", "shortfall", "default", "inspection finding"),
            partial_patterns=("remediation", "under review"),
        ),
        RegulationDefinition(
            regulation="SEBI / Capital Markets Compliance",
            regulator="Securities and Exchange Board of India",
            keywords=("sebi", "listed", "disclosure", "investor complaint"),
            positive_patterns=("filed", "current", "compliant"),
            negative_patterns=("debarred", "non-compliant", "penalty"),
            partial_patterns=("pending", "under review"),
        ),
    ),
}
NEGATIVE_OVERRIDES: dict[str, tuple[str, ...]] = {
    "sanctions": ("no sanctions",),
}


class RegulatoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)

    async def build_compliance_matrix(
        self,
        case_id: str,
        *,
        persist_checklist: bool = True,
    ) -> ComplianceMatrixSummary | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        snapshots = [
            snapshot
            for snapshot in collect_artifact_snapshots(case)
            if score_snapshot_relevance(
                snapshot,
                workstream_domains=("regulatory", "legal_corporate", "tax"),
                keywords=(
                    "mca",
                    "registration",
                    "licence",
                    "license",
                    "rbi",
                    "sebi",
                    "dpdp",
                    "consent to operate",
                    "pollution control",
                    "factory licence",
                ),
                document_kind_keywords=("regulatory", "mca", "license", "licence"),
            )
            > 0
        ]

        definitions = [*COMMON_REGULATIONS, *SECTOR_REGULATIONS.get(case.sector_pack, ())]
        items = [self._evaluate_regulation(definition, snapshots) for definition in definitions]
        flags = self._build_flags(items)

        summary = ComplianceMatrixSummary(
            case_id=case_id,
            sector_pack=SectorPack(case.sector_pack),
            items=items,
            flags=flags,
        )
        if persist_checklist:
            summary.checklist_updates = await self._auto_update_checklist(case, summary)
        return summary

    def _evaluate_regulation(
        self,
        definition: RegulationDefinition,
        snapshots: list[ArtifactTextSnapshot],
    ) -> ComplianceMatrixItem:
        matched_snapshots = [
            snapshot
            for snapshot in snapshots
            if any(keyword in snapshot.text.lower() for keyword in definition.keywords)
            or any(keyword in snapshot.title.lower() for keyword in definition.keywords)
            or any(keyword in snapshot.document_kind.lower() for keyword in definition.keywords)
        ]
        if not matched_snapshots:
            return ComplianceMatrixItem(
                regulation=definition.regulation,
                regulator=definition.regulator,
                status=ComplianceStatus.UNKNOWN,
                notes="No direct evidence was found for this regulation.",
            )

        joined = "\n".join(snapshot.text.lower() for snapshot in matched_snapshots)
        negative = self._contains_signal(
            joined,
            definition.negative_patterns,
            overrides=NEGATIVE_OVERRIDES,
        )
        partial = self._contains_signal(joined, definition.partial_patterns)
        positive = self._contains_signal(joined, definition.positive_patterns)
        if negative and partial:
            status = ComplianceStatus.PARTIALLY_COMPLIANT
        elif negative:
            status = ComplianceStatus.NON_COMPLIANT
        elif positive:
            status = ComplianceStatus.COMPLIANT
        elif partial:
            status = ComplianceStatus.PARTIALLY_COMPLIANT
        else:
            status = ComplianceStatus.UNKNOWN

        return ComplianceMatrixItem(
            regulation=definition.regulation,
            regulator=definition.regulator,
            status=status,
            evidence_ids=sorted(
                {
                    evidence_id
                    for snapshot in matched_snapshots
                    for evidence_id in snapshot.evidence_ids
                }
            ),
            notes=self._summarize_snapshot(matched_snapshots[0], len(matched_snapshots)),
        )

    def _build_flags(self, items: list[ComplianceMatrixItem]) -> list[str]:
        flags: list[str] = []
        for item in items:
            if item.status == ComplianceStatus.NON_COMPLIANT:
                flags.append(f"{item.regulation} appears non-compliant.")
            elif item.status == ComplianceStatus.PARTIALLY_COMPLIANT:
                flags.append(f"{item.regulation} appears partially compliant or under remediation.")
        return flags

    async def _auto_update_checklist(
        self,
        case,
        summary: ComplianceMatrixSummary,
    ) -> list[ChecklistAutoUpdate]:
        regulation_by_name = {item.regulation: item for item in summary.items}
        condition_map = {
            "regulatory.mca_consistency": regulation_by_name.get("MCA Statutory Filings")
            is not None
            and regulation_by_name["MCA Statutory Filings"].status != ComplianceStatus.UNKNOWN,
            "regulatory.licensing_and_borrowing_constraints": any(
                item.status != ComplianceStatus.UNKNOWN
                for item in summary.items
                if item.regulation
                in {
                    "Licensing / Registration Restrictions",
                    "RBI NBFC Registration",
                    "RBI / Prudential Returns",
                }
            ),
            "regulatory.vendor_restrictions": any(
                item.status != ComplianceStatus.UNKNOWN
                for item in summary.items
                if item.regulation
                in {
                    "Licensing / Registration Restrictions",
                }
            ),
            "regulatory.ehs_factory_compliance": any(
                item.status != ComplianceStatus.UNKNOWN
                for item in summary.items
                if item.regulation in {"Factory Licence", "Environmental / PCB Consent"}
            ),
            "regulatory.rbi_registration_and_returns": any(
                item.status != ComplianceStatus.UNKNOWN
                for item in summary.items
                if item.regulation in {"RBI NBFC Registration", "RBI / Prudential Returns"}
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

    def _build_checklist_note(self, summary: ComplianceMatrixSummary) -> str:
        known_items = [item for item in summary.items if item.status != ComplianceStatus.UNKNOWN]
        fragments = [
            "Auto-satisfied by Phase 9 Regulatory engine.",
            f"Compliance items with evidence: {len(known_items)}.",
        ]
        if known_items:
            fragments.append(
                "Statuses: "
                + ", ".join(f"{item.regulation}={item.status.value}" for item in known_items[:4])
                + "."
            )
        return " ".join(fragments)

    def _summarize_snapshot(
        self,
        snapshot: ArtifactTextSnapshot,
        match_count: int,
    ) -> str:
        cleaned = " ".join(snapshot.text.split())
        prefix = f"Matched {match_count} artifact(s). "
        if len(cleaned) <= 180:
            return prefix + cleaned
        return prefix + f"{cleaned[:177]}..."

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
