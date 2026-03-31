from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.db.models import AuditLogRecord


async def record_audit_event(
    session: AsyncSession,
    *,
    org_id: str | None,
    actor_id: str | None,
    actor_email: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    ip_address: str | None = None,
    request_id: str | None = None,
    status_code: int | None = None,
) -> AuditLogRecord:
    original_skip_audit = session.info.get("skip_audit", False)
    session.info["skip_audit"] = True
    try:
        record = AuditLogRecord(
            org_id=org_id,
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
            request_id=request_id,
            status_code=status_code,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record
    finally:
        session.info["skip_audit"] = original_skip_audit
