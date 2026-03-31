from __future__ import annotations

from typing import Any

from crewai_enterprise_pipeline_api.core.settings import Settings
from crewai_enterprise_pipeline_api.domain.models import (
    ArtifactSourceKind,
    EvidenceKind,
    SourceAdapterCategory,
    WorkstreamDomain,
)
from crewai_enterprise_pipeline_api.source_adapters.base import BaseSourceAdapter, RawFetchResult


class SebiScoresSourceAdapter(BaseSourceAdapter):
    adapter_id = "sebi_scores"
    aliases = ("listed_disclosures",)
    name = "SEBI SCORES / Listed Disclosures"
    purpose = "Capture investor complaints and listed-entity disclosure posture."
    category = SourceAdapterCategory.PUBLIC
    source_kind = ArtifactSourceKind.LISTED_DISCLOSURE
    workstream_domain = WorkstreamDomain.REGULATORY
    evidence_kind = EvidenceKind.GOVERNANCE
    document_kind = "sebi_scores_profile"
    supports_live_credentials = False
    requires_api_key = False
    fallback_mode = "stub_or_uploaded_exchange_export"
    identifier_label = "Company or Ticker"
    base_url_setting_name = "sebi_scores_api_base_url"

    async def fetch_live(
        self,
        identifier: str,
        *,
        settings: Settings,
        **params: Any,
    ) -> RawFetchResult:
        base_url = settings.sebi_scores_api_base_url.rstrip("/")
        payload = await self._request_json(
            url=f"{base_url}/scores/{identifier}",
            settings=settings,
            params=params or None,
        )
        return self._json_result(
            identifier=identifier,
            title=f"SEBI SCORES profile :: {identifier}",
            filename=f"sebi_scores_{self._safe_identifier(identifier)}.json",
            payload=payload,
        )

    def build_stub_result(self, identifier: str, **params: Any) -> RawFetchResult:
        payload = {
            "entity": identifier,
            "pending_investor_complaints": 2,
            "resolved_last_quarter": 11,
            "disclosures": [
                {"title": "Quarterly investor grievance report", "date": "2026-01-15"},
                {"title": "Outcome of board meeting", "date": "2026-02-05"},
            ],
            "debarment_status": "Not debarred",
        }
        return self._json_result(
            identifier=identifier,
            title=f"SEBI SCORES profile :: {identifier}",
            filename=f"sebi_scores_{self._safe_identifier(identifier)}.json",
            payload=payload,
        )

    def parse(self, raw: RawFetchResult) -> str:
        payload = self._decode_json(raw)
        lines = [
            "# SEBI SCORES and Listed Disclosure Profile",
            f"Entity: {payload['entity']}",
            f"Pending investor complaints: {payload['pending_investor_complaints']}",
            f"Resolved complaints in last quarter: {payload['resolved_last_quarter']}",
            f"Debarment status: {payload['debarment_status']}",
            "",
            "## Recent Disclosures",
        ]
        for disclosure in payload.get("disclosures", []):
            lines.append(f"- {disclosure['date']}: {disclosure['title']}")
        return "\n".join(lines)
