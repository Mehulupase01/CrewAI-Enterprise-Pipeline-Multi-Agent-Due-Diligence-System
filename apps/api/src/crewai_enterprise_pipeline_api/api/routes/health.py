from datetime import UTC, datetime

from fastapi import APIRouter

from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.domain.models import (
    AppHealth,
    FlagSeverity,
    MotionPack,
    PlatformOverview,
    SectorPack,
    WorkstreamDomain,
)

router = APIRouter()


@router.get("/health", response_model=AppHealth)
def health() -> AppHealth:
    settings = get_settings()
    return AppHealth(
        status="ok",
        environment=settings.app_env,
        version=settings.app_version,
        timestamp=datetime.now(UTC),
        enabled_motion_packs=[MotionPack.BUY_SIDE_DILIGENCE],
        enabled_sector_packs=[SectorPack.TECH_SAAS_SERVICES],
    )


@router.get("/overview", response_model=PlatformOverview)
def overview() -> PlatformOverview:
    return PlatformOverview(
        product_name="CrewAI Enterprise Pipeline",
        current_phase="Phase 0 / Phase 1 foundation",
        country="India",
        motion_packs=list(MotionPack),
        sector_packs=list(SectorPack),
        workstream_domains=list(WorkstreamDomain),
        severity_scale=list(FlagSeverity),
    )
