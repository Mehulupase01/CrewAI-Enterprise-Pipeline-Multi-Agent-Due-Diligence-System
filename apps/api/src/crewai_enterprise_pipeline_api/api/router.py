from fastapi import APIRouter

from crewai_enterprise_pipeline_api.api.routes.cases import router as case_router
from crewai_enterprise_pipeline_api.api.routes.health import router as system_router
from crewai_enterprise_pipeline_api.api.routes.source_adapters import (
    router as source_adapter_router,
)

api_router = APIRouter()
api_router.include_router(system_router, prefix="/system", tags=["system"])
api_router.include_router(
    source_adapter_router,
    prefix="/source-adapters",
    tags=["source-adapters"],
)
api_router.include_router(case_router, prefix="/cases", tags=["cases"])
