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


class GstinSourceAdapter(BaseSourceAdapter):
    adapter_id = "gstin"
    aliases = ("gstin_compliance",)
    name = "GSTIN Verification"
    purpose = "Verify GSTIN registration status, filing history, and notice posture."
    category = SourceAdapterCategory.PUBLIC
    source_kind = ArtifactSourceKind.PUBLIC_REGISTRY
    workstream_domain = WorkstreamDomain.TAX
    evidence_kind = EvidenceKind.FACT
    document_kind = "gstin_profile"
    supports_live_credentials = True
    requires_api_key = True
    fallback_mode = "stub_in_dev_or_manual_export"
    identifier_label = "GSTIN"
    base_url_setting_name = "gstin_api_base_url"
    api_key_setting_name = "gstin_api_key"

    async def fetch_live(
        self,
        identifier: str,
        *,
        settings: Settings,
        **params: Any,
    ) -> RawFetchResult:
        base_url = settings.gstin_api_base_url.rstrip("/")
        headers = {"X-API-Key": settings.gstin_api_key or ""}
        payload = await self._request_json(
            url=f"{base_url}/gstin/{identifier}",
            settings=settings,
            params=params or None,
            headers=headers,
        )
        return self._json_result(
            identifier=identifier,
            title=f"GSTIN profile :: {identifier}",
            filename=f"gstin_{self._safe_identifier(identifier)}.json",
            payload=payload,
        )

    def build_stub_result(self, identifier: str, **params: Any) -> RawFetchResult:
        payload = {
            "gstin": identifier,
            "legal_name": "Horizon Analytics Private Limited",
            "trade_name": "Horizon Analytics",
            "registration_status": "Active",
            "state": "Karnataka",
            "filing_history": [
                {
                    "return_type": "GSTR-3B",
                    "period": "2025-12",
                    "status": "Filed",
                    "filed_on": "2026-01-20",
                },
                {
                    "return_type": "GSTR-1",
                    "period": "2025-12",
                    "status": "Filed",
                    "filed_on": "2026-01-11",
                },
            ],
            "notices": [
                {
                    "subject": "Mismatch on input tax credit",
                    "status": "Under response",
                    "issued_on": "2025-11-02",
                }
            ],
        }
        return self._json_result(
            identifier=identifier,
            title=f"GSTIN profile :: {identifier}",
            filename=f"gstin_{self._safe_identifier(identifier)}.json",
            payload=payload,
        )

    def parse(self, raw: RawFetchResult) -> str:
        payload = self._decode_json(raw)
        lines = [
            "# GSTIN Registration and Filing Profile",
            f"GSTIN: {payload['gstin']}",
            f"Legal Name: {payload['legal_name']}",
            f"Trade Name: {payload['trade_name']}",
            f"Registration Status: {payload['registration_status']}",
            f"State: {payload['state']}",
            "",
            "## Filing History",
        ]
        for filing in payload.get("filing_history", []):
            lines.append(
                f"- {filing['return_type']} for {filing['period']} is {filing['status']} "
                f"(filed on {filing['filed_on']})"
            )
        lines.extend(["", "## Notices"])
        for notice in payload.get("notices", []):
            lines.append(
                "- Notice: "
                f"{notice['subject']} | Status: {notice['status']} | "
                f"Issued On: {notice['issued_on']}"
            )
        return "\n".join(lines)
