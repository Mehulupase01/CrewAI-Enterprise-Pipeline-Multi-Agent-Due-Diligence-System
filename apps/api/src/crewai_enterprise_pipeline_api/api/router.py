from fastapi import APIRouter

from crewai_enterprise_pipeline_api.api.routes.health import router as system_router

api_router = APIRouter()
api_router.include_router(system_router, prefix="/system", tags=["system"])
