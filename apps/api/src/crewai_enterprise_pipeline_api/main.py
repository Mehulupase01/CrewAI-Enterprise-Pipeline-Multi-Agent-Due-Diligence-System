from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from crewai_enterprise_pipeline_api.api.router import api_router
from crewai_enterprise_pipeline_api.core.logging import configure_logging
from crewai_enterprise_pipeline_api.core.rate_limit import get_rate_limiter
from crewai_enterprise_pipeline_api.core.security_utils import TokenDecodeError, decode_access_token
from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.db.session import close_database, get_database
from crewai_enterprise_pipeline_api.services.audit_service import record_audit_event

logger = logging.getLogger(__name__)


async def _try_connect_redis(app: FastAPI) -> None:
    """Attempt to create an arq Redis pool and store it on app.state.

    If Redis is unreachable (e.g., dev/test without Docker), log a warning
    and leave ``app.state.redis_pool`` as ``None``.
    """
    settings = get_settings()
    if not settings.background_mode:
        app.state.redis_pool = None
        return

    try:
        from arq.connections import RedisSettings, create_pool

        pool = await create_pool(RedisSettings(host=settings.redis_host, port=settings.redis_port))
        app.state.redis_pool = pool
        logger.info("Redis pool connected (%s:%s)", settings.redis_host, settings.redis_port)
    except Exception:
        logger.warning("Redis unavailable — background_mode disabled at runtime", exc_info=True)
        app.state.redis_pool = None


async def _close_redis(app: FastAPI) -> None:
    pool = getattr(app.state, "redis_pool", None)
    if pool is not None:
        pool.close()
        await pool.wait_closed()


def _resolve_rate_limit_scope(
    request: Request,
) -> tuple[str, int] | None:
    settings = get_settings()
    path = request.url.path

    if not path.startswith(settings.api_prefix):
        return None
    if path in {f"{settings.api_prefix}/docs", f"{settings.api_prefix}/openapi.json"}:
        return None

    if path == f"{settings.api_prefix}/auth/token":
        identity = request.client.host if request.client else "unknown"
        return f"auth:{identity}", settings.rate_limit_auth_per_minute

    org_identity: str | None = None
    authorization = request.headers.get("Authorization")
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            try:
                org_identity = decode_access_token(token, settings).org_id
            except TokenDecodeError:
                org_identity = None
    elif settings.header_auth_allowed and request.headers.get("X-CEP-User-Id"):
        org_identity = request.headers.get("X-CEP-Org-Id") or settings.default_org_id
    elif not settings.auth_required:
        org_identity = settings.default_org_id

    identity = org_identity or (request.client.host if request.client else "unknown")

    if path.endswith("/fetch") and "/source-adapters/" in path:
        return f"connector:{identity}", settings.rate_limit_connector_per_minute
    if request.method.upper() in {"POST", "PATCH", "PUT", "DELETE"}:
        return f"mutating:{identity}", settings.rate_limit_mutating_per_minute
    return f"read:{identity}", settings.rate_limit_read_per_minute


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    database = get_database()

    if settings.auto_create_schema:
        await database.create_schema()
    else:
        await database.ensure_runtime_defaults()

    await _try_connect_redis(app)

    yield

    await get_rate_limiter().close()
    await _close_redis(app)
    await close_database()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.app_env)

    app = FastAPI(
        title=settings.project_name,
        version=settings.app_version,
        docs_url=f"{settings.api_prefix}/docs",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def attach_request_context(request: Request, call_next):
        request_id = request.headers.get(settings.request_id_header_name) or str(uuid4())
        request.state.request_id = request_id

        limit_scope = _resolve_rate_limit_scope(request)
        if limit_scope is not None:
            limiter = get_rate_limiter()
            bucket, limit = limit_scope
            allowed, remaining = await limiter.hit(
                f"rate_limit:{bucket}",
                limit=limit,
                window_seconds=60,
            )
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded."},
                    headers={
                        settings.request_id_header_name: request_id,
                        "X-RateLimit-Remaining": str(remaining),
                    },
                )

        response = await call_next(request)

        failure_context = getattr(request.state, "auth_failure_context", None)
        if failure_context and response.status_code in {400, 401, 403}:
            database = get_database()
            async with database.session() as session:
                await record_audit_event(
                    session,
                    org_id=failure_context.get("org_id"),
                    actor_id=failure_context.get("actor_id"),
                    actor_email=failure_context.get("actor_email"),
                    action=failure_context.get("action", "AUTH_FAILURE"),
                    resource_type="auth",
                    resource_id=request.url.path,
                    after_state={"detail": failure_context.get("detail")},
                    ip_address=request.client.host if request.client else None,
                    request_id=request_id,
                    status_code=failure_context.get("status_code", response.status_code),
                )

        response.headers[settings.request_id_header_name] = request_id
        return response

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
