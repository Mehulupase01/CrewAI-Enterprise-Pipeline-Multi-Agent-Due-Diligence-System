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


class Mca21SourceAdapter(BaseSourceAdapter):
    adapter_id = "mca21"
    aliases = ("mca_public_records",)
    name = "MCA21 Public Records"
    purpose = "Fetch Indian company master data, directors, charges, and filing posture."
    category = SourceAdapterCategory.PUBLIC
    source_kind = ArtifactSourceKind.PUBLIC_REGISTRY
    workstream_domain = WorkstreamDomain.LEGAL_CORPORATE
    evidence_kind = EvidenceKind.GOVERNANCE
    document_kind = "mca21_master_data"
    supports_live_credentials = False
    requires_api_key = False
    fallback_mode = "stub_or_manual_export"
    identifier_label = "CIN"
    base_url_setting_name = "mca21_api_base_url"

    async def fetch_live(
        self,
        identifier: str,
        *,
        settings: Settings,
        **params: Any,
    ) -> RawFetchResult:
        base_url = settings.mca21_api_base_url.rstrip("/")
        payload = await self._request_json(
            url=f"{base_url}/company/master-data/{identifier}",
            settings=settings,
            params=params or None,
        )
        return self._json_result(
            identifier=identifier,
            title=f"MCA21 company master data :: {identifier}",
            filename=f"mca21_{self._safe_identifier(identifier)}.json",
            payload=payload,
        )

    def build_stub_result(self, identifier: str, **params: Any) -> RawFetchResult:
        payload = {
            "cin": identifier,
            "company_name": "Horizon Analytics Private Limited",
            "company_status": "Active",
            "incorporation_date": "2019-04-11",
            "registered_office": "Bengaluru, Karnataka, India",
            "directors": [
                {"name": "Mehul Shah", "din": "12345678", "designation": "Director"},
                {"name": "Riya Kapoor", "din": "23456789", "designation": "Director"},
            ],
            "shareholding": [
                {"holder": "Mehul Shah", "ownership_percent": 62.0},
                {"holder": "Alpha Growth Fund", "ownership_percent": 38.0},
            ],
            "charges": [
                {
                    "charge_holder": "HDFC Bank Limited",
                    "amount_inr": 12500000,
                    "status": "Open",
                }
            ],
            "annual_filings": [
                {
                    "year": "FY24",
                    "annual_return_status": "Filed",
                    "financial_statement_status": "Filed",
                },
                {
                    "year": "FY25",
                    "annual_return_status": "Filed",
                    "financial_statement_status": "Filed",
                },
            ],
        }
        return self._json_result(
            identifier=identifier,
            title=f"MCA21 company master data :: {identifier}",
            filename=f"mca21_{self._safe_identifier(identifier)}.json",
            payload=payload,
        )

    def parse(self, raw: RawFetchResult) -> str:
        payload = self._decode_json(raw)
        lines = [
            "# MCA21 Company Master Data",
            f"CIN: {payload['cin']}",
            f"Company Name: {payload['company_name']}",
            f"Company Status: {payload['company_status']}",
            f"Incorporation Date: {payload['incorporation_date']}",
            f"Registered Office: {payload['registered_office']}",
            "",
            "## Directors",
        ]
        for director in payload.get("directors", []):
            lines.append(
                f"- {director['name']} | DIN {director['din']} | {director['designation']}"
            )
        lines.extend(["", "## Shareholding"])
        for holder in payload.get("shareholding", []):
            lines.append(
                f"- Shareholder: {holder['holder']} | Ownership: {holder['ownership_percent']}%"
            )
        lines.extend(["", "## Charges"])
        for charge in payload.get("charges", []):
            lines.append(
                "- Charge Holder: "
                f"{charge['charge_holder']} | Amount: INR {charge['amount_inr']} | "
                f"Status: {charge['status']}"
            )
        lines.extend(["", "## Annual Filing Status"])
        for filing in payload.get("annual_filings", []):
            lines.append(
                f"- {filing['year']}: Annual return {filing['annual_return_status']}; "
                f"financial statements {filing['financial_statement_status']}"
            )
        return "\n".join(lines)
