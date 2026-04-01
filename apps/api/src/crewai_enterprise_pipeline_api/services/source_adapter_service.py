from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.core.telemetry import observe_connector_fetch
from crewai_enterprise_pipeline_api.domain.models import (
    DocumentIngestionResult,
    SourceAdapterFetchRequest,
    SourceAdapterSummary,
)
from crewai_enterprise_pipeline_api.source_adapters import (
    get_adapter_catalog,
    resolve_source_adapter,
)


class SourceAdapterService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_adapters(self) -> list[SourceAdapterSummary]:
        return get_adapter_catalog()

    async def fetch_into_case(
        self,
        *,
        case_id: str,
        adapter_key: str,
        payload: SourceAdapterFetchRequest,
    ) -> DocumentIngestionResult | None:
        adapter = resolve_source_adapter(adapter_key)
        if adapter is None:
            return None
        with observe_connector_fetch(adapter_key=adapter.adapter_id):
            return await adapter.ingest(
                case_id=case_id,
                identifier=payload.identifier,
                session=self.session,
                params=payload.params,
            )
