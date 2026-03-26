from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter
from sqlalchemy import text

from crewai_enterprise_pipeline_api.api.dependencies import DbSession
from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.domain.models import (
    AppHealth,
    FlagSeverity,
    MotionPack,
    PlatformOverview,
    ReadinessComponent,
    ReadinessReport,
    SectorPack,
    UserRole,
    WorkstreamDomain,
)

router = APIRouter()
EVALUATION_ROOT = Path(__file__).resolve().parents[6] / "artifacts" / "evaluations"


@router.get("/health", response_model=AppHealth)
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
            MotionPack.BUY_SIDE_DILIGENCE,
            MotionPack.CREDIT_LENDING,
            MotionPack.VENDOR_ONBOARDING,
        ],
        enabled_sector_packs=[SectorPack.TECH_SAAS_SERVICES],
    )


@router.get("/readiness", response_model=ReadinessReport)
async def readiness(session: DbSession) -> ReadinessReport:
    settings = get_settings()
    components: list[ReadinessComponent] = []

    database_status = "ok"
    database_detail = "Database connection succeeded."
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        database_status = "failed"
        database_detail = f"Database check failed: {exc}"
    components.append(
        ReadinessComponent(
            name="database",
            status=database_status,
            detail=database_detail,
        )
    )

    if settings.storage_backend == "local":
        storage_detail = f"Local storage root: {Path(settings.local_storage_root).resolve()}"
    else:
        storage_detail = f"Object storage endpoint: {settings.minio_endpoint}"
    components.append(
        ReadinessComponent(
            name="storage",
            status="ok",
            detail=storage_detail,
        )
    )

    artifacts = sorted(EVALUATION_ROOT.glob("*.json"))
    if artifacts:
        latest_artifact = artifacts[-1]
        evaluation_status = "ok"
        evaluation_detail = (
            f"Latest evaluation artifact: {latest_artifact.name}"
        )
    else:
        evaluation_status = "warning"
        evaluation_detail = "No evaluation artifact has been generated yet."
    components.append(
        ReadinessComponent(
            name="evaluation_baseline",
            status=evaluation_status,
            detail=evaluation_detail,
        )
    )

    overall_status = (
        "ready"
        if all(component.status in {"ok", "warning"} for component in components)
        and database_status == "ok"
        else "degraded"
    )
    return ReadinessReport(
        status=overall_status,
        environment=settings.app_env,
        timestamp=datetime.now(UTC),
        auth_required=settings.auth_required,
        components=components,
    )


@router.get("/overview", response_model=PlatformOverview)
def overview() -> PlatformOverview:
    settings = get_settings()
    return PlatformOverview(
        product_name="CrewAI Enterprise Pipeline",
        current_phase="Expansion Phase 2: vendor onboarding",
        country="India",
        auth_required=settings.auth_required,
        motion_packs=list(MotionPack),
        sector_packs=list(SectorPack),
        workstream_domains=list(WorkstreamDomain),
        severity_scale=list(FlagSeverity),
    )
