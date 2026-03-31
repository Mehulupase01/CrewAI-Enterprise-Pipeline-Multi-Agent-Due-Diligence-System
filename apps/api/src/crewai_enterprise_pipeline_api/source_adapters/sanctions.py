from __future__ import annotations

import csv
from difflib import SequenceMatcher
from io import StringIO
from typing import Any

from crewai_enterprise_pipeline_api.core.settings import Settings
from crewai_enterprise_pipeline_api.domain.models import (
    ArtifactSourceKind,
    EvidenceKind,
    SourceAdapterCategory,
    WorkstreamDomain,
)
from crewai_enterprise_pipeline_api.source_adapters.base import BaseSourceAdapter, RawFetchResult


class SanctionsSourceAdapter(BaseSourceAdapter):
    adapter_id = "sanctions"
    aliases = ("sanctions_watchlists",)
    name = "Sanctions and Watchlists"
    purpose = "Screen company and promoter names against public sanctions and debarment lists."
    category = SourceAdapterCategory.PUBLIC
    source_kind = ArtifactSourceKind.PUBLIC_REGISTRY
    workstream_domain = WorkstreamDomain.FORENSIC_COMPLIANCE
    evidence_kind = EvidenceKind.RISK
    document_kind = "sanctions_screening"
    supports_live_credentials = False
    requires_api_key = False
    fallback_mode = "stub_in_dev"
    identifier_label = "Company or promoter name"

    def is_live_configured(self, settings: Settings) -> bool:
        return bool(
            settings.sanctions_ofac_url
            and settings.sanctions_mca_url
            and settings.sanctions_sebi_url
        )

    async def fetch_live(
        self,
        identifier: str,
        *,
        settings: Settings,
        **params: Any,
    ) -> RawFetchResult:
        list_texts = {
            "OFAC SDN": await self._request_text(
                url=settings.sanctions_ofac_url,
                settings=settings,
            ),
            "MCA Disqualified Directors": await self._request_text(
                url=settings.sanctions_mca_url,
                settings=settings,
            ),
            "SEBI Debarred Entities": await self._request_text(
                url=settings.sanctions_sebi_url,
                settings=settings,
            ),
        }
        payload = self._screen_identifier(
            identifier,
            list_texts,
            extra_subjects=params.get("aliases", ()),
        )
        return self._json_result(
            identifier=identifier,
            title=f"Sanctions screening :: {identifier}",
            filename=f"sanctions_{self._safe_identifier(identifier)}.json",
            payload=payload,
        )

    def build_stub_result(self, identifier: str, **params: Any) -> RawFetchResult:
        list_texts = {
            "OFAC SDN": "name\nAcme Sanctions Trading LLP\nVector Finvest Limited\n",
            "MCA Disqualified Directors": "name\nRogue Director\nDisqualified Promoter\n",
            "SEBI Debarred Entities": "name\nVector Finvest Limited\n",
        }
        payload = self._screen_identifier(
            identifier,
            list_texts,
            extra_subjects=params.get("aliases", ()),
        )
        return self._json_result(
            identifier=identifier,
            title=f"Sanctions screening :: {identifier}",
            filename=f"sanctions_{self._safe_identifier(identifier)}.json",
            payload=payload,
        )

    def parse(self, raw: RawFetchResult) -> str:
        payload = self._decode_json(raw)
        lines = [
            "# Sanctions and Watchlist Screening",
            f"Query: {payload['query']}",
            "",
            "## Matches",
        ]
        matches = payload.get("matches", [])
        if matches:
            for match in matches:
                lines.append(
                    f"- Subject: {match['subject']} | List: {match['list_name']} | "
                    f"Matched Name: {match['matched_name']} | Score: {match['score']}"
                )
        else:
            lines.append("- No sanctions, disqualification, or debarment matches were found.")
        return "\n".join(lines)

    def _screen_identifier(
        self,
        identifier: str,
        list_texts: dict[str, str],
        *,
        extra_subjects: tuple[str, ...] | list[str],
    ) -> dict[str, Any]:
        subjects = [identifier, *extra_subjects]
        matches: list[dict[str, Any]] = []
        for subject in subjects:
            subject_normalized = subject.strip().lower()
            if not subject_normalized:
                continue
            for list_name, text in list_texts.items():
                for candidate in self._candidate_names(text):
                    score = self._score(subject_normalized, candidate.lower())
                    if score >= 0.9:
                        matches.append(
                            {
                                "subject": subject,
                                "list_name": list_name,
                                "matched_name": candidate,
                                "score": round(score, 3),
                            }
                        )
        return {"query": identifier, "matches": matches}

    def _candidate_names(self, text: str) -> list[str]:
        if "," in text:
            reader = csv.reader(StringIO(text))
            names: list[str] = []
            for row in reader:
                if not row:
                    continue
                first = row[0].strip()
                if first and first.lower() != "name":
                    names.append(first)
            return names
        return [
            line.strip()
            for line in text.splitlines()
            if line.strip() and line.strip().lower() != "name"
        ]

    def _score(self, subject: str, candidate: str) -> float:
        if subject == candidate:
            return 1.0
        if subject in candidate or candidate in subject:
            return 0.95
        return SequenceMatcher(a=subject, b=candidate).ratio()
