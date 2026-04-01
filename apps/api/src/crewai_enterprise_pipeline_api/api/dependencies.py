from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.api.security import get_current_principal
from crewai_enterprise_pipeline_api.db.session import get_database
from crewai_enterprise_pipeline_api.domain.models import AuthenticatedPrincipal


async def get_raw_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    database = get_database()
    async with database.session() as session:
        session.info["request_id"] = getattr(request.state, "request_id", None)
        session.info["ip_address"] = request.client.host if request.client else None
        yield session


async def get_db_session(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
) -> AsyncGenerator[AsyncSession, None]:
    database = get_database()
    async with database.session() as session:
        session.info["request_id"] = getattr(request.state, "request_id", None)
        session.info["ip_address"] = request.client.host if request.client else None
        session.info["actor_id"] = principal.user_id
        session.info["actor_email"] = principal.email
        session.info["org_id"] = principal.org_id
        session.info["allow_cross_org"] = principal.role.value == "admin"
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db_session)]
RawDbSession = Annotated[AsyncSession, Depends(get_raw_db_session)]
