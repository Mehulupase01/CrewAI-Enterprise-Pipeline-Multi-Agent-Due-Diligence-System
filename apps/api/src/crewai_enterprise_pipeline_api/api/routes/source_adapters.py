from fastapi import APIRouter

from crewai_enterprise_pipeline_api.domain.models import SourceAdapterSummary
from crewai_enterprise_pipeline_api.ingestion.adapters.contracts import get_adapter_catalog

router = APIRouter()


@router.get("", response_model=list[SourceAdapterSummary])
async def list_source_adapters() -> list[SourceAdapterSummary]:
    return get_adapter_catalog()
