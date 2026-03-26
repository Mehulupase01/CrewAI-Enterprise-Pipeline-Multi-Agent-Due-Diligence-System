from fastapi import FastAPI

from crewai_enterprise_pipeline_api.api.router import api_router
from crewai_enterprise_pipeline_api.core.logging import configure_logging
from crewai_enterprise_pipeline_api.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.app_env)

    app = FastAPI(
        title=settings.project_name,
        version=settings.app_version,
        docs_url=f"{settings.api_prefix}/docs",
        openapi_url=f"{settings.api_prefix}/openapi.json",
    )
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
