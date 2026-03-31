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


class CibilSourceAdapter(BaseSourceAdapter):
    adapter_id = "cibil"
    aliases = ("vendor_connector", "cibil_stub")
    name = "CIBIL Bureau Connector"
    purpose = "Production-shaped bureau adapter with stubbed dev/test data for lender workflows."
    category = SourceAdapterCategory.VENDOR
    source_kind = ArtifactSourceKind.VENDOR_CONNECTOR
    workstream_domain = WorkstreamDomain.FINANCIAL_QOE
    evidence_kind = EvidenceKind.METRIC
    document_kind = "cibil_bureau_report"
    supports_live_credentials = True
    requires_api_key = True
    fallback_mode = "stub_in_dev"
    identifier_label = "Borrower PAN or bureau ID"
    base_url_setting_name = "cibil_api_base_url"
    api_key_setting_name = "cibil_api_key"

    async def fetch_live(
        self,
        identifier: str,
        *,
        settings: Settings,
        **params: Any,
    ) -> RawFetchResult:
        base_url = settings.cibil_api_base_url.rstrip("/")
        headers = {"X-API-Key": settings.cibil_api_key or ""}
        payload = await self._request_json(
            url=f"{base_url}/bureau/{identifier}",
            settings=settings,
            params=params or None,
            headers=headers,
        )
        return self._json_result(
            identifier=identifier,
            title=f"CIBIL bureau summary :: {identifier}",
            filename=f"cibil_{self._safe_identifier(identifier)}.json",
            payload=payload,
        )

    def build_stub_result(self, identifier: str, **params: Any) -> RawFetchResult:
        payload = {
            "borrower_id": identifier,
            "bureau_score": 742,
            "active_accounts": 4,
            "overdue_accounts": 0,
            "days_past_due_max": 0,
            "recent_inquiries": 2,
            "watchouts": ["No overdue accounts reported in the last 24 months."],
        }
        return self._json_result(
            identifier=identifier,
            title=f"CIBIL bureau summary :: {identifier}",
            filename=f"cibil_{self._safe_identifier(identifier)}.json",
            payload=payload,
        )

    def parse(self, raw: RawFetchResult) -> str:
        payload = self._decode_json(raw)
        lines = [
            "# CIBIL Bureau Summary",
            f"Borrower ID: {payload['borrower_id']}",
            f"Bureau Score: {payload['bureau_score']}",
            f"Active Accounts: {payload['active_accounts']}",
            f"Overdue Accounts: {payload['overdue_accounts']}",
            f"Maximum Days Past Due: {payload['days_past_due_max']}",
            f"Recent Inquiries: {payload['recent_inquiries']}",
            "",
            "## Watchouts",
        ]
        for item in payload.get("watchouts", []):
            lines.append(f"- {item}")
        return "\n".join(lines)
