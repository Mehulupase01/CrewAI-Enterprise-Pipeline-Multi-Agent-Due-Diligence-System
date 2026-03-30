"""arq worker module — background job definitions and WorkerSettings.

Usage:
    arq crewai_enterprise_pipeline_api.worker.WorkerSettings
"""

from __future__ import annotations

import logging

from arq.connections import RedisSettings

from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.db.session import get_database
from crewai_enterprise_pipeline_api.domain.models import WorkflowRunCreate
from crewai_enterprise_pipeline_api.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)


async def run_workflow_job(ctx: dict, case_id: str, requested_by: str, note: str | None) -> str:
    """Execute a workflow run inside the arq worker process."""
    database = get_database()
    async with database.session_factory() as session:
        service = WorkflowService(session)
        payload = WorkflowRunCreate(requested_by=requested_by, note=note)
        result = await service.execute_run(case_id, payload)
        if result is None:
            logger.error("Workflow job for case %s failed: case not found", case_id)
            return f"case_not_found:{case_id}"
        return f"completed:{result.run.id}"


async def startup(ctx: dict) -> None:
    """Worker startup — initialise the database connection."""
    settings = get_settings()
    logger.info("arq worker starting (concurrency=%d)", settings.worker_concurrency)
    database = get_database()
    if settings.auto_create_schema:
        await database.create_schema()


async def shutdown(ctx: dict) -> None:
    """Worker shutdown — close the database pool."""
    from crewai_enterprise_pipeline_api.db.session import close_database

    await close_database()
    logger.info("arq worker shut down")


def _redis_settings() -> RedisSettings:
    settings = get_settings()
    return RedisSettings(host=settings.redis_host, port=settings.redis_port)


class WorkerSettings:
    """arq WorkerSettings — run with: arq crewai_enterprise_pipeline_api.worker.WorkerSettings"""

    functions = [run_workflow_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings()
    max_jobs = get_settings().worker_concurrency
