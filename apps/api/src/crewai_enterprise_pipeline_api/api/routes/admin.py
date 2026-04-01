from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from crewai_enterprise_pipeline_api.api.dependencies import DbSession
from crewai_enterprise_pipeline_api.api.security import require_admin_access
from crewai_enterprise_pipeline_api.domain.models import (
    AuditLogListResponse,
    AuthenticatedPrincipal,
    DependencyStatusReport,
    LlmProviderSummary,
    OrgLlmRuntimeConfig,
    OrgLlmRuntimeConfigUpdate,
)
from crewai_enterprise_pipeline_api.services.admin_service import AdminService
from crewai_enterprise_pipeline_api.services.dependency_probe_service import DependencyProbeService
from crewai_enterprise_pipeline_api.services.runtime_control_service import (
    LlmRuntimeUnavailableError,
    RuntimeControlService,
)

router = APIRouter(dependencies=[Depends(require_admin_access)])


@router.get("/audit-log", response_model=AuditLogListResponse)
async def list_audit_logs(
    session: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    org_id: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
) -> AuditLogListResponse:
    return await AdminService(session).list_audit_logs(
        skip=skip,
        limit=limit,
        org_id=org_id,
        action=action,
        resource_type=resource_type,
    )


@router.get("/system/dependencies", response_model=DependencyStatusReport)
async def list_dependency_statuses(session: DbSession) -> DependencyStatusReport:
    return await DependencyProbeService(session).get_latest_report()


@router.post("/system/dependencies/refresh", response_model=DependencyStatusReport)
async def refresh_dependency_statuses(session: DbSession) -> DependencyStatusReport:
    return await DependencyProbeService(session).refresh_and_persist()


@router.get("/system/llm/providers", response_model=list[LlmProviderSummary])
async def list_runtime_llm_providers(session: DbSession) -> list[LlmProviderSummary]:
    return await RuntimeControlService(session).list_llm_providers()


@router.get("/system/llm/default", response_model=OrgLlmRuntimeConfig)
async def get_runtime_llm_default(
    session: DbSession,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_admin_access)],
) -> OrgLlmRuntimeConfig:
    return await RuntimeControlService(session).get_org_llm_default(principal.org_id)


@router.patch("/system/llm/default", response_model=OrgLlmRuntimeConfig)
async def update_runtime_llm_default(
    payload: OrgLlmRuntimeConfigUpdate,
    session: DbSession,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_admin_access)],
) -> OrgLlmRuntimeConfig:
    service = RuntimeControlService(session)
    try:
        return await service.update_org_llm_default(principal.org_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LlmRuntimeUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
