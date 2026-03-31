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


class RocFilingsSourceAdapter(BaseSourceAdapter):
    adapter_id = "roc_filings"
    aliases = ("roc",)
    name = "RoC Filings"
    purpose = "Fetch charges, registrar orders, and winding-up petition context."
    category = SourceAdapterCategory.PUBLIC
    source_kind = ArtifactSourceKind.PUBLIC_REGISTRY
    workstream_domain = WorkstreamDomain.LEGAL_CORPORATE
    evidence_kind = EvidenceKind.GOVERNANCE
    document_kind = "roc_filings_profile"
    supports_live_credentials = False
    requires_api_key = False
    fallback_mode = "stub_or_manual_export"
    identifier_label = "CIN"
    base_url_setting_name = "roc_api_base_url"

    async def fetch_live(
        self,
        identifier: str,
        *,
        settings: Settings,
        **params: Any,
    ) -> RawFetchResult:
        base_url = settings.roc_api_base_url.rstrip("/")
        payload = await self._request_json(
            url=f"{base_url}/roc/{identifier}",
            settings=settings,
            params=params or None,
        )
        return self._json_result(
            identifier=identifier,
            title=f"RoC filings :: {identifier}",
            filename=f"roc_{self._safe_identifier(identifier)}.json",
            payload=payload,
        )

    def build_stub_result(self, identifier: str, **params: Any) -> RawFetchResult:
        payload = {
            "cin": identifier,
            "charges": [
                {"holder": "ICICI Bank", "amount_inr": 8500000, "status": "Satisfied"},
                {"holder": "HDFC Bank", "amount_inr": 12500000, "status": "Open"},
            ],
            "orders": [
                {
                    "authority": "Registrar of Companies",
                    "subject": "Additional filing fee order",
                    "date": "2025-08-19",
                }
            ],
            "winding_up_petitions": [],
        }
        return self._json_result(
            identifier=identifier,
            title=f"RoC filings :: {identifier}",
            filename=f"roc_{self._safe_identifier(identifier)}.json",
            payload=payload,
        )

    def parse(self, raw: RawFetchResult) -> str:
        payload = self._decode_json(raw)
        lines = [
            "# Registrar of Companies Filings",
            f"CIN: {payload['cin']}",
            "",
            "## Charges",
        ]
        for charge in payload.get("charges", []):
            lines.append(
                f"- Charge holder: {charge['holder']} | Amount: INR {charge['amount_inr']} "
                f"| Status: {charge['status']}"
            )
        lines.extend(["", "## Orders"])
        for order in payload.get("orders", []):
            lines.append(f"- {order['date']} | {order['authority']} | {order['subject']}")
        lines.extend(["", "## Winding-up Petitions"])
        petitions = payload.get("winding_up_petitions", [])
        if petitions:
            for petition in petitions:
                lines.append(
                    f"- {petition['court']} | {petition['petition_no']} | {petition['status']}"
                )
        else:
            lines.append("- No winding-up petitions were reported.")
        return "\n".join(lines)
