from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.domain.models import (
    ChecklistAutoUpdate,
    ChecklistItemStatus,
    ContractClauseReview,
    ContractReviewResult,
    DirectorProfile,
    LegalStructureSummary,
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

DIN_PATTERN = re.compile(r"\b\d{8}\b")
SHAREHOLDING_PATTERN = re.compile(
    r"\b(promoter|public|fii|institutional|employee trust)\b[^0-9%]{0,25}"
    r"(\d{1,3}(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
SUBSIDIARY_PATTERN = re.compile(
    r"\b(?:subsidiary|wholly owned subsidiary|step-?down subsidiary)\b[:\s-]*"
    r"([A-Z][A-Za-z0-9&(), \-]{3,}?)"
    r"(?=\.|,|;|\n|$)",
    re.IGNORECASE,
)

STRUCTURE_SIGNAL_KEYWORDS = (
    "mca",
    "director",
    "din",
    "shareholding",
    "cap table",
    "subsidiary",
    "charge",
    "encumbrance",
)
CONTRACT_SIGNAL_KEYWORDS = (
    "agreement",
    "contract",
    "msa",
    "service agreement",
    "shareholders agreement",
    "sha",
    "loan agreement",
    "facility agreement",
    "vendor agreement",
    "customer agreement",
)

CLAUSE_PATTERNS: dict[str, tuple[str, ...]] = {
    "change_of_control": (
        "change of control",
        "change-of-control",
        "change in control",
    ),
    "assignment": ("assignment", "assign", "novation"),
    "termination": ("termination", "terminate", "termination for convenience"),
    "indemnity": ("indemnity", "indemnify", "hold harmless"),
    "liability_cap": (
        "limitation of liability",
        "liability cap",
        "aggregate liability",
    ),
    "governing_law": ("governing law", "laws of", "jurisdiction"),
    "exclusivity": ("exclusive", "exclusivity"),
    "non_compete": ("non-compete", "non compete", "restrictive covenant"),
}


class LegalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)

    async def build_legal_summary(
        self,
        case_id: str,
        *,
        persist_checklist: bool = True,
    ) -> LegalStructureSummary | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        snapshots = collect_artifact_snapshots(case)
        structure_snapshots = self._select_structure_snapshots(snapshots)
        contract_snapshots = self._select_contract_snapshots(snapshots)

        directors = self._extract_directors(structure_snapshots)
        shareholding_summary = self._extract_shareholding(structure_snapshots)
        subsidiary_mentions = self._extract_subsidiaries(structure_snapshots)
        charges_detected = self._count_charge_mentions(structure_snapshots)
        contract_reviews = self._review_contracts(contract_snapshots)
        flags = self._build_flags(
            structure_snapshots,
            contract_reviews,
            charges_detected,
            subsidiary_mentions,
        )

        summary = LegalStructureSummary(
            case_id=case_id,
            artifact_count=len(structure_snapshots) + len(contract_snapshots),
            directors=directors,
            shareholding_summary=shareholding_summary,
            charges_detected=charges_detected,
            subsidiary_mentions=subsidiary_mentions,
            contract_reviews=contract_reviews,
            flags=flags,
        )

        if persist_checklist:
            summary.checklist_updates = await self._auto_update_checklist(case, summary)
        return summary

    def _select_structure_snapshots(
        self,
        snapshots: list[ArtifactTextSnapshot],
    ) -> list[ArtifactTextSnapshot]:
        selected = [
            snapshot
            for snapshot in snapshots
            if score_snapshot_relevance(
                snapshot,
                workstream_domains=("legal_corporate", "regulatory"),
                keywords=STRUCTURE_SIGNAL_KEYWORDS,
                document_kind_keywords=("mca", "cap", "secretarial", "corporate"),
            )
            > 0
        ]
        return selected

    def _select_contract_snapshots(
        self,
        snapshots: list[ArtifactTextSnapshot],
    ) -> list[ArtifactTextSnapshot]:
        selected = [
            snapshot
            for snapshot in snapshots
            if score_snapshot_relevance(
                snapshot,
                workstream_domains=("legal_corporate",),
                keywords=CONTRACT_SIGNAL_KEYWORDS,
                document_kind_keywords=("contract", "agreement", "msa", "sha", "loan"),
            )
            > 0
        ]
        return selected

    def _extract_directors(
        self,
        snapshots: list[ArtifactTextSnapshot],
    ) -> list[DirectorProfile]:
        directors: dict[tuple[str, str | None], DirectorProfile] = {}
        for snapshot in snapshots:
            for line in snapshot.text.splitlines():
                matches = DIN_PATTERN.findall(line)
                if not matches:
                    continue
                for din in matches:
                    prefix = re.split(r"\bDIN\b", line, maxsplit=1, flags=re.IGNORECASE)[0]
                    name = prefix.strip(" -:;|()") or None
                    if name and len(name) > 120:
                        name = name[:120].strip()
                    profile = DirectorProfile(
                        name=name,
                        din=din,
                        din_valid_format=bool(DIN_PATTERN.fullmatch(din)),
                        source_artifact_id=snapshot.artifact_id,
                    )
                    directors[(profile.din, profile.source_artifact_id)] = profile
        return sorted(directors.values(), key=lambda item: (item.name or "", item.din))

    def _extract_shareholding(
        self,
        snapshots: list[ArtifactTextSnapshot],
    ) -> dict[str, float]:
        summary: dict[str, float] = {}
        for snapshot in snapshots:
            for holder, percentage in SHAREHOLDING_PATTERN.findall(snapshot.text):
                summary[holder.lower()] = round(float(percentage), 2)
        return dict(sorted(summary.items()))

    def _extract_subsidiaries(
        self,
        snapshots: list[ArtifactTextSnapshot],
    ) -> list[str]:
        names: set[str] = set()
        for snapshot in snapshots:
            for match in SUBSIDIARY_PATTERN.findall(snapshot.text):
                cleaned = re.sub(r"\s+", " ", match).strip(" .,:;|-")
                if cleaned:
                    names.add(cleaned)
        return sorted(names)

    def _count_charge_mentions(self, snapshots: list[ArtifactTextSnapshot]) -> int:
        total = 0
        for snapshot in snapshots:
            total += len(
                re.findall(
                    r"\b(charge|encumbrance|lien|pledge|security interest)\b",
                    snapshot.text,
                    re.IGNORECASE,
                )
            )
        return total

    def _review_contracts(
        self,
        snapshots: list[ArtifactTextSnapshot],
    ) -> list[ContractReviewResult]:
        reviews: list[ContractReviewResult] = []
        for snapshot in snapshots:
            text = snapshot.text.lower()
            clauses: list[ContractClauseReview] = []
            flags: list[str] = []
            for clause_key, patterns in CLAUSE_PATTERNS.items():
                present = any(pattern in text for pattern in patterns)
                note = self._clause_note(snapshot.text, patterns[0]) if present else "Not detected."
                clauses.append(
                    ContractClauseReview(
                        clause_key=clause_key,
                        present=present,
                        note=note,
                    )
                )

            governing_law = self._extract_governing_law(snapshot.text)
            if governing_law and "india" not in governing_law.lower():
                flags.append(
                    "Contract appears governed by "
                    f"{governing_law}, which may require foreign-law review."
                )
            if self._clause_present(clauses, "change_of_control"):
                flags.append(
                    "Change-of-control clause detected; review assignment and consent mechanics."
                )
            if self._clause_present(clauses, "indemnity") and not self._clause_present(
                clauses,
                "liability_cap",
            ):
                flags.append("Indemnity language detected without a clear liability cap reference.")

            review = ContractReviewResult(
                artifact_id=snapshot.artifact_id,
                contract_title=snapshot.title,
                contract_type=self._detect_contract_type(snapshot),
                governing_law=governing_law,
                clauses=clauses,
                flags=sorted(set(flags)),
            )
            if any(clause.present for clause in clauses):
                reviews.append(review)
        return reviews

    def _build_flags(
        self,
        structure_snapshots: list[ArtifactTextSnapshot],
        contract_reviews: list[ContractReviewResult],
        charges_detected: int,
        subsidiary_mentions: list[str],
    ) -> list[str]:
        haystack = "\n".join(snapshot.text for snapshot in structure_snapshots).lower()
        flags: list[str] = []
        if "circular shareholding" in haystack:
            flags.append("Potential circular shareholding reference detected in legal materials.")
        if "nominee director" in haystack:
            flags.append(
                "Nominee director reference detected; confirm governance rights and vetoes."
            )
        if "struck off" in haystack or "struck-off" in haystack:
            flags.append(
                "Struck-off entity reference detected; "
                "validate subsidiary and related-party universe."
            )
        if charges_detected:
            flags.append(
                "Charge or encumbrance references detected "
                f"{charges_detected} times across legal materials."
            )
        if len(subsidiary_mentions) >= 3:
            flags.append(
                "Multiple subsidiary references detected; confirm full corporate structure mapping."
            )
        flags.extend(flag for review in contract_reviews for flag in review.flags)
        return sorted(set(flags))

    async def _auto_update_checklist(
        self,
        case,
        summary: LegalStructureSummary,
    ) -> list[ChecklistAutoUpdate]:
        condition_map = {
            "legal_corporate.cap_table": bool(
                summary.directors or summary.shareholding_summary or summary.subsidiary_mentions
            ),
            "legal_corporate.material_contracts": bool(summary.contract_reviews),
            "legal_corporate.security_package": bool(
                summary.charges_detected
                or any(
                    review.contract_type in {"loan_agreement", "security_document"}
                    for review in summary.contract_reviews
                )
            ),
            "legal_corporate.vendor_registration": bool(summary.directors),
            "legal_corporate.contractual_risk": bool(summary.contract_reviews),
        }

        updated: list[ChecklistAutoUpdate] = []
        for item in case.checklist_items:
            template_key = item.template_key or ""
            if not condition_map.get(template_key):
                continue
            if item.status in COMPLETED_CHECKLIST_STATUSES:
                continue
            note = self._build_checklist_note(template_key, summary)
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

    def _build_checklist_note(
        self,
        template_key: str,
        summary: LegalStructureSummary,
    ) -> str:
        fragments = [
            "Auto-satisfied by Phase 9 Legal / Corporate engine.",
            f"Directors identified: {len(summary.directors)}.",
            f"Contract reviews: {len(summary.contract_reviews)}.",
        ]
        if summary.charges_detected:
            fragments.append(f"Charge references: {summary.charges_detected}.")
        if template_key.endswith("cap_table") and summary.shareholding_summary:
            fragments.append(
                "Shareholding signals: "
                + ", ".join(
                    f"{holder} {value:.2f}%"
                    for holder, value in summary.shareholding_summary.items()
                )
                + "."
            )
        return " ".join(fragments)

    def _detect_contract_type(self, snapshot: ArtifactTextSnapshot) -> str:
        text = " ".join(
            filter(None, [snapshot.title, snapshot.document_kind, snapshot.original_filename])
        ).lower()
        if "loan" in text or "facility" in text:
            return "loan_agreement"
        if "security" in text or "pledge" in text:
            return "security_document"
        if "shareholder" in text or "sha" in text:
            return "shareholders_agreement"
        if "vendor" in text or "supplier" in text:
            return "vendor_agreement"
        if "customer" in text:
            return "customer_agreement"
        return "commercial_contract"

    def _extract_governing_law(self, text: str) -> str | None:
        patterns = (
            r"governed by the laws of ([A-Za-z ,.()]+)",
            r"jurisdiction of ([A-Za-z ,.()]+)",
        )
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return re.sub(r"\s+", " ", match.group(1)).strip(" .,:;")
        return None

    def _clause_note(self, text: str, marker: str) -> str:
        match = re.search(re.escape(marker), text, re.IGNORECASE)
        if match is None:
            return "Detected."
        start = max(0, match.start() - 60)
        end = min(len(text), match.end() + 120)
        excerpt = " ".join(text[start:end].split())
        return excerpt or "Detected."

    def _clause_present(
        self,
        clauses: list[ContractClauseReview],
        clause_key: str,
    ) -> bool:
        return any(clause.clause_key == clause_key and clause.present for clause in clauses)
