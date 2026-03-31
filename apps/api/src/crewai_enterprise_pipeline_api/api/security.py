from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from crewai_enterprise_pipeline_api.core.security_utils import (
    TokenDecodeError,
    decode_access_token,
)
from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.domain.models import AuthenticatedPrincipal, UserRole


def _set_auth_failure_context(
    request: Request,
    *,
    action: str,
    detail: str,
    status_code: int,
    actor_id: str | None = None,
    actor_email: str | None = None,
    org_id: str | None = None,
) -> None:
    request.state.auth_failure_context = {
        "action": action,
        "detail": detail,
        "status_code": status_code,
        "actor_id": actor_id,
        "actor_email": actor_email,
        "org_id": org_id,
    }


def _build_header_principal(
    *,
    request: Request,
    user_id: str | None,
    user_name: str | None,
    user_email: str | None,
    user_role: str | None,
    org_id: str | None,
) -> AuthenticatedPrincipal:
    settings = get_settings()

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
        detail = "Missing authentication headers: " + ", ".join(missing_headers)
        _set_auth_failure_context(
            request,
            action="AUTH_FAILURE",
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            actor_id=user_id,
            actor_email=user_email,
            org_id=org_id or settings.default_org_id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )

    try:
        role = UserRole(user_role or "")
    except ValueError as exc:
        detail = "Invalid X-CEP-User-Role header."
        _set_auth_failure_context(
            request,
            action="AUTH_FAILURE",
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
            actor_id=user_id,
            actor_email=user_email,
            org_id=org_id or settings.default_org_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc

    return AuthenticatedPrincipal(
        user_id=user_id or "",
        name=user_name or "",
        email=user_email or "",
        role=role,
        org_id=org_id or settings.default_org_id,
        auth_required=settings.auth_required,
    )


def get_current_principal(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    user_id: Annotated[str | None, Header(alias="X-CEP-User-Id")] = None,
    user_name: Annotated[str | None, Header(alias="X-CEP-User-Name")] = None,
    user_email: Annotated[str | None, Header(alias="X-CEP-User-Email")] = None,
    user_role: Annotated[str | None, Header(alias="X-CEP-User-Role")] = None,
    org_id: Annotated[str | None, Header(alias="X-CEP-Org-Id")] = None,
) -> AuthenticatedPrincipal:
    settings = get_settings()

    principal: AuthenticatedPrincipal | None = None

    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            detail = "Authorization header must use Bearer <token>."
            _set_auth_failure_context(
                request,
                action="AUTH_FAILURE",
                detail=detail,
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
        try:
            principal = decode_access_token(token, settings)
        except TokenDecodeError as exc:
            _set_auth_failure_context(
                request,
                action="AUTH_FAILURE",
                detail=str(exc),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            ) from exc
    elif settings.header_auth_allowed and any(
        value is not None for value in (user_id, user_name, user_email, user_role, org_id)
    ):
        principal = _build_header_principal(
            request=request,
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            user_role=user_role,
            org_id=org_id,
        )
    elif not settings.auth_required:
        principal = AuthenticatedPrincipal(
            user_id=settings.default_actor_id,
            name=settings.default_actor_name,
            email=settings.default_actor_email,
            role=UserRole(settings.default_actor_role),
            org_id=settings.default_org_id,
            auth_required=False,
        )
    elif settings.header_auth_allowed:
        detail = (
            "Missing authentication. Provide a Bearer token or development headers."
        )
        _set_auth_failure_context(
            request,
            action="AUTH_FAILURE",
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            org_id=settings.default_org_id,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
    else:
        detail = "Missing bearer token."
        _set_auth_failure_context(
            request,
            action="AUTH_FAILURE",
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            org_id=settings.default_org_id,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

    request.state.principal = principal
    return principal


def require_roles(*allowed_roles: UserRole):
    def dependency(
        request: Request,
        principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    ) -> AuthenticatedPrincipal:
        if principal.role not in allowed_roles:
            allowed = ", ".join(role.value for role in allowed_roles)
            detail = f"Role '{principal.role.value}' cannot access this route. Allowed: {allowed}."
            _set_auth_failure_context(
                request,
                action="AUTHZ_FAILURE",
                detail=detail,
                status_code=status.HTTP_403_FORBIDDEN,
                actor_id=principal.user_id,
                actor_email=principal.email,
                org_id=principal.org_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
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
require_admin_access = require_roles(UserRole.ADMIN)
