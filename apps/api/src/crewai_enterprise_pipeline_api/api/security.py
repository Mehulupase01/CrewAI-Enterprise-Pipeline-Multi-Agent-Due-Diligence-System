from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.domain.models import AuthenticatedPrincipal, UserRole


def get_current_principal(
    request: Request,
    user_id: Annotated[str | None, Header(alias="X-CEP-User-Id")] = None,
    user_name: Annotated[str | None, Header(alias="X-CEP-User-Name")] = None,
    user_email: Annotated[str | None, Header(alias="X-CEP-User-Email")] = None,
    user_role: Annotated[str | None, Header(alias="X-CEP-User-Role")] = None,
) -> AuthenticatedPrincipal:
    settings = get_settings()

    if not settings.auth_required and user_id is None and user_role is None:
        principal = AuthenticatedPrincipal(
            user_id=settings.default_actor_id,
            name=settings.default_actor_name,
            email=settings.default_actor_email,
            role=UserRole(settings.default_actor_role),
            auth_required=False,
        )
        request.state.principal = principal
        return principal

    missing_headers = [
        header_name
        for header_name, value in (
            ("X-CEP-User-Id", user_id),
            ("X-CEP-User-Name", user_name),
            ("X-CEP-User-Email", user_email),
            ("X-CEP-User-Role", user_role),
        )
        if not value
    ]
    if missing_headers:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=("Missing authentication headers: " + ", ".join(missing_headers)),
        )

    try:
        role = UserRole(user_role or "")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-CEP-User-Role header.",
        ) from exc

    principal = AuthenticatedPrincipal(
        user_id=user_id or "",
        name=user_name or "",
        email=user_email or "",
        role=role,
        auth_required=settings.auth_required,
    )
    request.state.principal = principal
    return principal


def require_roles(*allowed_roles: UserRole):
    def dependency(
        principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    ) -> AuthenticatedPrincipal:
        if principal.role not in allowed_roles:
            allowed = ", ".join(role.value for role in allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{principal.role.value}' cannot access this route. Allowed: {allowed}."
                ),
            )
        return principal

    return dependency


require_read_access = require_roles(
    UserRole.VIEWER,
    UserRole.ANALYST,
    UserRole.REVIEWER,
    UserRole.ADMIN,
)
require_write_access = require_roles(
    UserRole.ANALYST,
    UserRole.REVIEWER,
    UserRole.ADMIN,
)
require_reviewer_access = require_roles(UserRole.REVIEWER, UserRole.ADMIN)
