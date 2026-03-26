from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request

from crewai_enterprise_pipeline_api.api.router import api_router
from crewai_enterprise_pipeline_api.core.logging import configure_logging
from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.db.session import close_database, get_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    database = get_database()

    if settings.auto_create_schema:
        await database.create_schema()

    yield

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
