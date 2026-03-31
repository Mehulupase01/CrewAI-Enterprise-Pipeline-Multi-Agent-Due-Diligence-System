from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.core.settings import Settings, get_settings
from crewai_enterprise_pipeline_api.domain.models import (
    ArtifactSourceKind,
    DocumentIngestionResult,
    EvidenceKind,
    SourceAdapterCategory,
    SourceAdapterStatus,
    SourceAdapterSummary,
    WorkstreamDomain,
)
from crewai_enterprise_pipeline_api.services.ingestion_service import IngestionService


class SourceAdapterError(RuntimeError):
    """Base class for connector-related failures."""


class SourceAdapterUnavailableError(SourceAdapterError):
    """Raised when an adapter has no live configuration outside stub mode."""


@dataclass(slots=True)
class RawFetchResult:
    identifier: str
    title: str
    filename: str
    mime_type: str
    content: bytes
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseSourceAdapter(ABC):
    adapter_id = "base"
    aliases: tuple[str, ...] = ()
    name = "Base Source Adapter"
    purpose = "Base adapter"
    category = SourceAdapterCategory.PUBLIC
    source_kind = ArtifactSourceKind.PUBLIC_REGISTRY
    workstream_domain = WorkstreamDomain.REGULATORY
    evidence_kind = EvidenceKind.FACT
    document_kind = "external_source_document"
    supports_india = True
    supports_live_credentials = False
    requires_api_key = False
    fallback_mode = "stub_in_dev"
    supports_fetch = True
    identifier_label = "identifier"
    base_url_setting_name: str | None = None
    api_key_setting_name: str | None = None

    def get_status(self, settings: Settings) -> SourceAdapterStatus:
        if not self.supports_fetch:
            return SourceAdapterStatus.AVAILABLE
        if self.is_live_configured(settings):
            return SourceAdapterStatus.AVAILABLE
        if settings.source_adapter_force_stub or settings.app_env in {"development", "test"}:
            return SourceAdapterStatus.STUB
        return SourceAdapterStatus.UNAVAILABLE

    def is_live_configured(self, settings: Settings) -> bool:
        if self.requires_api_key and not self._get_api_key(settings):
            return False
        if self.base_url_setting_name is None:
            return False
        base_url = getattr(settings, self.base_url_setting_name, None)
        return bool(base_url)

    def summary(self, settings: Settings) -> SourceAdapterSummary:
        return SourceAdapterSummary(
            adapter_key=self.adapter_id,
            category=self.category,
            title=self.name,
            purpose=self.purpose,
            supports_india=self.supports_india,
            supports_live_credentials=self.supports_live_credentials,
            requires_api_key=self.requires_api_key,
            status=self.get_status(settings),
            supports_fetch=self.supports_fetch,
            identifier_label=self.identifier_label,
            source_kind=self.source_kind,
            default_document_kind=self.document_kind,
            default_workstream_domain=self.workstream_domain,
            fallback_mode=self.fallback_mode,
        )

    async def ingest(
        self,
        *,
        case_id: str,
        identifier: str,
        session: AsyncSession,
        params: dict[str, Any] | None = None,
    ) -> DocumentIngestionResult | None:
        raw = await self.fetch(identifier, **(params or {}))
        parsed_text = self.parse(raw)
        return await IngestionService(session).ingest_connector_document(
            case_id=case_id,
            title=raw.title,
            filename=raw.filename,
            raw_content=raw.content,
            mime_type=raw.mime_type,
            document_kind=self.document_kind,
            source_kind=self.source_kind,
            workstream_domain=self.workstream_domain,
            evidence_kind=self.evidence_kind,
            parsed_text=parsed_text,
            parser_name=f"source_adapter:{self.adapter_id}",
        )

    async def fetch(self, identifier: str, **params: Any) -> RawFetchResult:
        settings = get_settings()
        if not self.supports_fetch:
            raise SourceAdapterUnavailableError(
                f"Adapter '{self.adapter_id}' is catalog-only and does not support fetch."
            )
        if self._should_use_stub(settings):
            return self.build_stub_result(identifier, **params)
        if not self.is_live_configured(settings):
            raise SourceAdapterUnavailableError(
                f"Adapter '{self.adapter_id}' has no live configuration in {settings.app_env} mode."
            )
        return await self.fetch_live(identifier, settings=settings, **params)

    def _should_use_stub(self, settings: Settings) -> bool:
        if settings.source_adapter_force_stub or settings.app_env == "test":
            return True
        return settings.app_env == "development" and not self.is_live_configured(settings)

    @abstractmethod
    async def fetch_live(
        self,
        identifier: str,
        *,
        settings: Settings,
        **params: Any,
    ) -> RawFetchResult:
        raise NotImplementedError

    @abstractmethod
    def build_stub_result(self, identifier: str, **params: Any) -> RawFetchResult:
        raise NotImplementedError

    @abstractmethod
    def parse(self, raw: RawFetchResult) -> str:
        raise NotImplementedError

    def _get_api_key(self, settings: Settings) -> str | None:
        if self.api_key_setting_name is None:
            return None
        return getattr(settings, self.api_key_setting_name, None)

    async def _request_json(
        self,
        *,
        url: str,
        settings: Settings,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        async with httpx.AsyncClient(
            timeout=settings.source_adapter_http_timeout_seconds
        ) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()

    async def _request_text(
        self,
        *,
        url: str,
        settings: Settings,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        async with httpx.AsyncClient(
            timeout=settings.source_adapter_http_timeout_seconds
        ) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.text

    def _json_result(
        self,
        *,
        identifier: str,
        title: str,
        filename: str,
        payload: dict[str, Any],
    ) -> RawFetchResult:
        return RawFetchResult(
            identifier=identifier,
            title=title,
            filename=filename,
            mime_type="application/json",
            content=json.dumps(payload, indent=2, sort_keys=True).encode("utf-8"),
            metadata=payload,
        )

    def _decode_json(self, raw: RawFetchResult) -> dict[str, Any]:
        if raw.metadata:
            return dict(raw.metadata)
        return json.loads(raw.content.decode("utf-8"))

    def _safe_identifier(self, identifier: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", identifier.strip())
        return safe or "lookup"
