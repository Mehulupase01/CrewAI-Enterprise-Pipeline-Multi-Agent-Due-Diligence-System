from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request

from crewai_enterprise_pipeline_api.api.router import api_router
from crewai_enterprise_pipeline_api.core.logging import configure_logging
from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.db.session import close_database, get_database

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    database = get_database()

    if settings.auto_create_schema:
        await database.create_schema()

    await _try_connect_redis(app)

    yield

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
        response = await call_next(request)
        response.headers[settings.request_id_header_name] = request_id
        return response

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
