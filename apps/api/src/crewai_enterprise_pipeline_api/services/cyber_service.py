from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.domain.models import (
    ChecklistAutoUpdate,
    ChecklistItemStatus,
    ComplianceStatus,
    CyberControlCheck,
    CyberPrivacySummary,
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
class CyberControlDefinition:
    control_key: str
    keywords: tuple[str, ...]
    positive_patterns: tuple[str, ...]
    negative_patterns: tuple[str, ...]
    partial_patterns: tuple[str, ...] = ()


CONTROL_DEFINITIONS: tuple[CyberControlDefinition, ...] = (
    CyberControlDefinition(
        control_key="consent_mechanism",
        keywords=("consent", "consent mechanism", "notice", "opt-in"),
        positive_patterns=("implemented", "current", "compliant", "captured"),
        negative_patterns=("missing consent", "no consent", "consent gap"),
        partial_patterns=("draft", "in progress", "under remediation"),
    ),
    CyberControlDefinition(
        control_key="purpose_limitation",
        keywords=("purpose limitation", "data map", "processing purpose"),
        positive_patterns=("documented", "implemented", "current"),
        negative_patterns=("not documented", "missing", "gap"),
        partial_patterns=("in progress", "under review"),
    ),
    CyberControlDefinition(
        control_key="retention_policy",
        keywords=("retention policy", "retention schedule", "deletion policy"),
        positive_patterns=("approved", "implemented", "current"),
        negative_patterns=("absent", "missing", "expired"),
        partial_patterns=("draft", "pending approval", "under remediation"),
    ),
    CyberControlDefinition(
        control_key="breach_notification",
        keywords=("breach notification", "incident response", "notification procedure"),
        positive_patterns=("tested", "documented", "implemented"),
        negative_patterns=("missing", "not tested", "gap"),
        partial_patterns=("tabletop planned", "in progress", "under review"),
    ),
    CyberControlDefinition(
        control_key="significant_data_fiduciary_registration",
        keywords=("significant data fiduciary", "sdf", "dpbi", "data protection board"),
        positive_patterns=("registered", "notified", "current"),
        negative_patterns=("not registered", "missing registration"),
        partial_patterns=("pending", "under review"),
    ),
    CyberControlDefinition(
        control_key="iso_27001",
        keywords=("iso 27001", "iso27001"),
        positive_patterns=("certified", "current", "valid"),
        negative_patterns=("expired", "lapsed", "not certified"),
        partial_patterns=("audit in progress", "pending certification"),
    ),
    CyberControlDefinition(
        control_key="soc2",
        keywords=("soc 2", "soc2"),
        positive_patterns=("certified", "type ii", "current"),
        negative_patterns=("failed", "not certified", "no soc 2", "no soc2", "gap"),
        partial_patterns=("audit in progress", "pending"),
    ),
    CyberControlDefinition(
        control_key="kyc_aml_data_controls",
        keywords=("kyc", "ckyc", "aml", "customer data", "consent"),
        positive_patterns=("current", "implemented", "compliant"),
        negative_patterns=("backlog", "gap", "missing", "weakness"),
        partial_patterns=("under remediation", "pending"),
    ),
)

CYBER_KEYWORDS = (
    "dpdp",
    "privacy",
    "consent",
    "retention",
    "breach",
    "incident response",
    "iso 27001",
    "soc2",
    "kyc",
    "aml",
    "customer data",
)
BREACH_KEYWORDS = (
    "data breach",
    "security incident",
    "privacy incident",
    "ransomware",
    "unauthorized access",
    "data leak",
)
CONTROL_LABELS: dict[str, str] = {
    "consent_mechanism": "Consent mechanism",
    "purpose_limitation": "Purpose limitation",
    "retention_policy": "Retention policy",
    "breach_notification": "Breach notification procedure",
    "significant_data_fiduciary_registration": "Significant Data Fiduciary registration",
    "iso_27001": "ISO 27001",
    "soc2": "SOC 2",
    "kyc_aml_data_controls": "KYC / AML data controls",
}


class CyberService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)

    async def build_cyber_summary(
        self,
        case_id: str,
        *,
        persist_checklist: bool = True,
    ) -> CyberPrivacySummary | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        snapshots = self._select_snapshots(collect_artifact_snapshots(case))
        controls = [
            self._evaluate_control(definition, snapshots) for definition in CONTROL_DEFINITIONS
        ]
        certifications = self._extract_certifications(controls)
        breach_history = self._extract_breach_history(snapshots)
        flags = self._build_flags(controls, certifications, breach_history)

        summary = CyberPrivacySummary(
            case_id=case_id,
            controls=controls,
            certifications=certifications,
            breach_history=breach_history,
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
                workstream_domains=("cyber_privacy", "operations", "regulatory"),
                keywords=CYBER_KEYWORDS,
                document_kind_keywords=("security", "privacy", "dpdp", "cyber", "infosec"),
            )
            > 0
        ]

    def _evaluate_control(
        self,
        definition: CyberControlDefinition,
        snapshots: list[ArtifactTextSnapshot],
    ) -> CyberControlCheck:
        matched_snapshots = [
            snapshot
            for snapshot in snapshots
            if any(keyword in snapshot.text.lower() for keyword in definition.keywords)
            or any(keyword in snapshot.title.lower() for keyword in definition.keywords)
            or any(keyword in snapshot.document_kind.lower() for keyword in definition.keywords)
        ]
        if not matched_snapshots:
            return CyberControlCheck(
                control_key=definition.control_key,
                status=ComplianceStatus.UNKNOWN,
                notes="No direct evidence was found for this control.",
            )

        windows = [
            window
            for snapshot in matched_snapshots
            for window in self._keyword_windows(snapshot.text, definition.keywords)
        ]
        joined = (
            "\n".join(windows).lower()
            if windows
            else "\n".join(snapshot.text.lower() for snapshot in matched_snapshots)
        )
        positive_patterns = self._positive_patterns_for_control(definition.control_key)
        negative = self._contains_signal(joined, definition.negative_patterns)
        partial = self._contains_signal(joined, definition.partial_patterns)
        positive = self._contains_signal(joined, positive_patterns)
        if negative and positive:
            status = ComplianceStatus.PARTIALLY_COMPLIANT
        elif negative:
            status = ComplianceStatus.NON_COMPLIANT
        elif positive and partial:
            status = ComplianceStatus.PARTIALLY_COMPLIANT
        elif positive:
            status = ComplianceStatus.COMPLIANT
        elif partial:
            status = ComplianceStatus.PARTIALLY_COMPLIANT
        else:
            status = ComplianceStatus.UNKNOWN

        return CyberControlCheck(
            control_key=definition.control_key,
            status=status,
            notes=self._summarize_snapshot(matched_snapshots[0], len(matched_snapshots)),
            evidence_ids=sorted(
                {
                    evidence_id
                    for snapshot in matched_snapshots
                    for evidence_id in snapshot.evidence_ids
                }
            ),
        )

    def _extract_certifications(
        self,
        controls: list[CyberControlCheck],
    ) -> list[str]:
        certifications: list[str] = []
        control_by_key = {control.control_key: control for control in controls}
        iso_control = control_by_key.get("iso_27001")
        soc2_control = control_by_key.get("soc2")
        if iso_control is not None and iso_control.status in {
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.PARTIALLY_COMPLIANT,
        }:
            certifications.append("ISO 27001")
        if soc2_control is not None and soc2_control.status in {
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.PARTIALLY_COMPLIANT,
        }:
            certifications.append("SOC 2")
        return certifications

    def _extract_breach_history(
        self,
        snapshots: list[ArtifactTextSnapshot],
    ) -> list[str]:
        breaches: list[str] = []
        for snapshot in snapshots:
            for sentence in self._sentences(snapshot.text):
                lowered = sentence.lower()
                if any(keyword in lowered for keyword in BREACH_KEYWORDS):
                    cleaned = " ".join(sentence.split())
                    if cleaned not in breaches:
                        breaches.append(cleaned)
        return breaches[:5]

    def _build_flags(
        self,
        controls: list[CyberControlCheck],
        certifications: list[str],
        breach_history: list[str],
    ) -> list[str]:
        flags: list[str] = []
        for control in controls:
            label = CONTROL_LABELS.get(control.control_key, control.control_key)
            if control.status == ComplianceStatus.NON_COMPLIANT:
                flags.append(f"{label} appears non-compliant.")
            elif control.status == ComplianceStatus.PARTIALLY_COMPLIANT:
                flags.append(f"{label} appears partially compliant or under remediation.")
        if not certifications:
            flags.append(
                "No ISO 27001 or SOC 2 certification signal was detected in cyber materials."
            )
        if breach_history:
            flags.append("Cyber or privacy incident history was detected in uploaded materials.")
        return flags

    async def _auto_update_checklist(
        self,
        case,
        summary: CyberPrivacySummary,
    ) -> list[ChecklistAutoUpdate]:
        known_controls = [
            item for item in summary.controls if item.status != ComplianceStatus.UNKNOWN
        ]
        has_signals = bool(known_controls or summary.certifications or summary.breach_history)
        condition_map = {
            "cyber.privacy_controls": has_signals,
            "cyber_privacy.vendor_security_posture": has_signals,
            "cyber_privacy.kyc_aml_and_data_controls": bool(
                summary.certifications
                or any(
                    item.control_key
                    in {
                        "kyc_aml_data_controls",
                        "consent_mechanism",
                        "retention_policy",
                    }
                    and item.status != ComplianceStatus.UNKNOWN
                    for item in summary.controls
                )
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

    def _build_checklist_note(self, summary: CyberPrivacySummary) -> str:
        known_controls = [
            item for item in summary.controls if item.status != ComplianceStatus.UNKNOWN
        ]
        fragments = [
            "Auto-satisfied by Phase 10 Cyber / Privacy engine.",
            f"Controls with evidence: {len(known_controls)}.",
        ]
        if summary.certifications:
            fragments.append("Certifications: " + ", ".join(summary.certifications) + ".")
        if summary.breach_history:
            fragments.append(f"Breach signals: {len(summary.breach_history)}.")
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

    def _contains_signal(self, text: str, patterns: tuple[str, ...]) -> bool:
        return any(self._phrase_present(text, pattern) for pattern in patterns)

    def _positive_patterns_for_control(self, control_key: str) -> tuple[str, ...]:
        if control_key == "iso_27001":
            return ("iso 27001 certified", "iso27001 certified", "iso 27001 current")
        if control_key == "soc2":
            return (
                "soc 2 certified",
                "soc2 certified",
                "soc 2 type ii",
                "soc2 type ii",
                "soc 2 current",
                "soc2 current",
            )
        return next(
            (
                definition.positive_patterns
                for definition in CONTROL_DEFINITIONS
                if definition.control_key == control_key
            ),
            (),
        )

    def _keyword_windows(self, text: str, keywords: tuple[str, ...]) -> list[str]:
        windows: list[str] = []
        lowered = text.lower()
        for keyword in keywords:
            index = lowered.find(keyword.lower())
            if index < 0:
                continue
            start = max(0, index - 90)
            end = min(len(text), index + len(keyword) + 120)
            windows.append(text[start:end])
        return windows

    def _phrase_present(self, text: str, phrase: str) -> bool:
        escaped = re.escape(phrase.strip().lower()).replace(r"\ ", r"\s+")
        return bool(re.search(rf"(?<!\w){escaped}(?!\w)", text))

    def _sentences(self, text: str) -> list[str]:
        return [
            segment.strip() for segment in re.split(r"(?<=[.!?])\s+|\n+", text) if segment.strip()
        ]
