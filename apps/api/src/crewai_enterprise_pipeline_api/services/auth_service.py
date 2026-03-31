from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.core.security_utils import (
    issue_access_token,
    verify_client_secret,
)
from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.db.models import ApiClientRecord
from crewai_enterprise_pipeline_api.domain.models import TokenRequest, TokenResponse, UserRole
from crewai_enterprise_pipeline_api.services.audit_service import record_audit_event


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def issue_client_token(
        self,
        payload: TokenRequest,
        *,
        request_id: str | None,
        ip_address: str | None,
    ) -> TokenResponse | None:
        settings = get_settings()
        result = await self.session.execute(
            select(ApiClientRecord)
            .execution_options(skip_org_scope=True)
            .where(ApiClientRecord.client_id == payload.client_id)
        )
        client = result.scalar_one_or_none()
        if client is None or not client.active:
            return None
        if not verify_client_secret(payload.client_secret, client.client_secret_hash):
            return None

        token, expires_in = issue_access_token(
            actor_id=client.client_id,
            actor_name=client.display_name,
            actor_email=client.actor_email,
            role=client.role,
            org_id=client.org_id,
            settings=settings,
        )
        await record_audit_event(
            self.session,
            org_id=client.org_id,
            actor_id=client.client_id,
            actor_email=client.actor_email,
            action="AUTH_TOKEN_ISSUED",
            resource_type="api_clients",
            resource_id=client.id,
            after_state={"client_id": client.client_id, "role": client.role},
            ip_address=ip_address,
            request_id=request_id,
            status_code=200,
        )
        return TokenResponse(
            access_token=token,
            expires_in=expires_in,
            actor_id=client.client_id,
            actor_email=client.actor_email,
            org_id=client.org_id,
            role=UserRole(client.role),
        )
