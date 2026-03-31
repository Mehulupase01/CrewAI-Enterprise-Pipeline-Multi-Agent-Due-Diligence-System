from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.db.models import AuditLogRecord
from crewai_enterprise_pipeline_api.domain.models import AuditLogEntry, AuditLogListResponse


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_audit_logs(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        org_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
    ) -> AuditLogListResponse:
        filters = []
        if org_id:
            filters.append(AuditLogRecord.org_id == org_id)
        if action:
            filters.append(AuditLogRecord.action == action)
        if resource_type:
            filters.append(AuditLogRecord.resource_type == resource_type)

        total_result = await self.session.execute(
            select(func.count()).select_from(AuditLogRecord).where(*filters)
        )
        total = int(total_result.scalar_one())

        result = await self.session.execute(
            select(AuditLogRecord)
            .where(*filters)
            .order_by(AuditLogRecord.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return AuditLogListResponse(
            total=total,
            items=[AuditLogEntry.model_validate(item) for item in result.scalars().all()],
        )
