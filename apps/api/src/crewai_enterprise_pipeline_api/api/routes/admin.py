from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from crewai_enterprise_pipeline_api.api.dependencies import DbSession
from crewai_enterprise_pipeline_api.api.security import require_admin_access
from crewai_enterprise_pipeline_api.domain.models import AuditLogListResponse
from crewai_enterprise_pipeline_api.services.admin_service import AdminService

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
