from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from crewai_enterprise_pipeline_api.api.dependencies import DbSession, RawDbSession
from crewai_enterprise_pipeline_api.api.security import require_read_access
from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.core.telemetry import render_metrics_payload
from crewai_enterprise_pipeline_api.domain.models import (
    AppHealth,
    AuthenticatedPrincipal,
    DependencyStatusReport,
    FlagSeverity,
    LivenessReport,
    LlmProviderSummary,
    MotionPack,
    OrgLlmRuntimeConfig,
    PlatformOverview,
    ReadinessComponent,
    ReadinessReport,
    SectorPack,
    UserRole,
    WorkstreamDomain,
)
from crewai_enterprise_pipeline_api.services.dependency_probe_service import DependencyProbeService
from crewai_enterprise_pipeline_api.services.runtime_control_service import RuntimeControlService

system_router = APIRouter()
health_router = APIRouter()


@system_router.get("/health", response_model=AppHealth)
def health() -> AppHealth:
    settings = get_settings()
    return AppHealth(
        status="ok",
        environment=settings.app_env,
        version=settings.app_version,
        timestamp=datetime.now(UTC),
        auth_required=settings.auth_required,
        default_actor_role=UserRole(settings.default_actor_role),
        request_id_header_name=settings.request_id_header_name,
        enabled_motion_packs=[
            MotionPack(p.strip()) for p in settings.enabled_motion_packs.split(",") if p.strip()
        ],
        enabled_sector_packs=[
            SectorPack(p.strip()) for p in settings.enabled_sector_packs.split(",") if p.strip()
        ],
    )


@health_router.get("/health/liveness", response_model=LivenessReport)
def liveness() -> LivenessReport:
    settings = get_settings()
    return LivenessReport(
        status="alive",
        environment=settings.app_env,
        timestamp=datetime.now(UTC),
    )


@health_router.get("/health/readiness", response_model=DependencyStatusReport)
async def readiness_snapshot(session: RawDbSession) -> DependencyStatusReport:
    return await DependencyProbeService(session).build_report()


@system_router.get("/readiness", response_model=ReadinessReport)
async def readiness(session: RawDbSession) -> ReadinessReport:
    report = await DependencyProbeService(session).build_report()
    components = [
        ReadinessComponent(
            name=dependency.name,
            status=dependency.status.value,
            detail=(
                f"[{dependency.category.value}/{dependency.mode.value}] {dependency.detail} "
                f"(latency_ms={dependency.latency_ms})"
            ),
        )
        for dependency in report.dependencies
    ]
    return ReadinessReport(
        status="ready" if report.status == "ok" else "degraded",
        environment=report.environment,
        timestamp=report.timestamp,
        auth_required=report.auth_required,
        components=components,
    )


@system_router.get(
    "/dependencies",
    response_model=DependencyStatusReport,
    dependencies=[Depends(require_read_access)],
)
async def list_system_dependencies(session: DbSession) -> DependencyStatusReport:
    return await DependencyProbeService(session).get_latest_report()


@system_router.get(
    "/llm/providers",
    response_model=list[LlmProviderSummary],
    dependencies=[Depends(require_read_access)],
)
async def list_llm_providers(session: DbSession) -> list[LlmProviderSummary]:
    return await RuntimeControlService(session).list_llm_providers()


@system_router.get(
    "/llm/default",
    response_model=OrgLlmRuntimeConfig,
    dependencies=[Depends(require_read_access)],
)
async def get_llm_default(
    session: DbSession,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_read_access)],
) -> OrgLlmRuntimeConfig:
    return await RuntimeControlService(session).get_org_llm_default(principal.org_id)


@health_router.get("/metrics")
def metrics() -> Response:
    payload, media_type = render_metrics_payload()
    return Response(content=payload, media_type=media_type)


@system_router.get("/overview", response_model=PlatformOverview)
def overview() -> PlatformOverview:
    settings = get_settings()
    return PlatformOverview(
        product_name=settings.product_name,
        current_phase=settings.current_phase,
        country=settings.country,
        auth_required=settings.auth_required,
        motion_packs=list(MotionPack),
        sector_packs=list(SectorPack),
        workstream_domains=list(WorkstreamDomain),
        severity_scale=list(FlagSeverity),
    )
