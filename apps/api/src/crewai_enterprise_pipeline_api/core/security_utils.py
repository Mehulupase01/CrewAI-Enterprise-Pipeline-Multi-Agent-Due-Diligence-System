from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta

import jwt

from crewai_enterprise_pipeline_api.core.settings import Settings
from crewai_enterprise_pipeline_api.domain.models import AuthenticatedPrincipal, UserRole


class TokenDecodeError(ValueError):
    pass


def hash_client_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def verify_client_secret(secret: str, expected_hash: str) -> bool:
    computed_hash = hash_client_secret(secret)
    return hmac.compare_digest(computed_hash, expected_hash)


def issue_access_token(
    *,
    actor_id: str,
    actor_name: str,
    actor_email: str,
    role: str,
    org_id: str,
    settings: Settings,
) -> tuple[str, int]:
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.jwt_access_token_expires_seconds)
    payload = {
        "sub": actor_id,
        "name": actor_name,
        "email": actor_email,
        "role": role,
        "org_id": org_id,
        "exp": expires_at,
        "iat": datetime.now(UTC),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, settings.jwt_access_token_expires_seconds


def decode_access_token(token: str, settings: Settings) -> AuthenticatedPrincipal:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise TokenDecodeError("Invalid or expired bearer token.") from exc

    try:
        role = UserRole(payload["role"])
    except (KeyError, ValueError) as exc:
        raise TokenDecodeError("Bearer token payload is missing a valid role.") from exc

    required_keys = ("sub", "name", "email", "org_id")
    missing_keys = [key for key in required_keys if not payload.get(key)]
    if missing_keys:
        raise TokenDecodeError(
            "Bearer token payload is missing required fields: " + ", ".join(missing_keys)
        )

    return AuthenticatedPrincipal(
        user_id=str(payload["sub"]),
        name=str(payload["name"]),
        email=str(payload["email"]),
        role=role,
        org_id=str(payload["org_id"]),
        auth_required=settings.auth_required,
    )
