from __future__ import annotations

from functools import lru_cache

from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.domain.models import (
    ArtifactSourceKind,
    SourceAdapterCategory,
    SourceAdapterStatus,
    SourceAdapterSummary,
)
from crewai_enterprise_pipeline_api.source_adapters.base import BaseSourceAdapter
from crewai_enterprise_pipeline_api.source_adapters.cibil import CibilSourceAdapter
from crewai_enterprise_pipeline_api.source_adapters.gstin import GstinSourceAdapter
from crewai_enterprise_pipeline_api.source_adapters.mca21 import Mca21SourceAdapter
from crewai_enterprise_pipeline_api.source_adapters.roc import RocFilingsSourceAdapter
from crewai_enterprise_pipeline_api.source_adapters.sanctions import SanctionsSourceAdapter
from crewai_enterprise_pipeline_api.source_adapters.sebi_scores import SebiScoresSourceAdapter


@lru_cache
def get_registered_adapters() -> tuple[BaseSourceAdapter, ...]:
    return (
        Mca21SourceAdapter(),
        GstinSourceAdapter(),
        SebiScoresSourceAdapter(),
        RocFilingsSourceAdapter(),
        CibilSourceAdapter(),
        SanctionsSourceAdapter(),
    )


def resolve_source_adapter(adapter_key: str) -> BaseSourceAdapter | None:
    normalized = adapter_key.strip().lower()
    for adapter in get_registered_adapters():
        if normalized == adapter.adapter_id or normalized in adapter.aliases:
            return adapter
    return None


def get_adapter_catalog() -> list[SourceAdapterSummary]:
    settings = get_settings()
    catalog: list[SourceAdapterSummary] = [
        SourceAdapterSummary(
            adapter_key="uploaded_dataroom",
            category=SourceAdapterCategory.UPLOADED,
            title="Uploaded Data Room",
            purpose=(
                "Accept private diligence artifacts from secure uploads and "
                "operator-managed folders."
            ),
            supports_india=True,
            supports_live_credentials=False,
            requires_api_key=False,
            status=SourceAdapterStatus.AVAILABLE,
            supports_fetch=False,
            identifier_label=None,
            source_kind=ArtifactSourceKind.UPLOADED_DATAROOM,
            default_document_kind="uploaded_artifact",
            default_workstream_domain=None,
            fallback_mode="primary",
        )
    ]
    catalog.extend(adapter.summary(settings) for adapter in get_registered_adapters())
    return catalog
