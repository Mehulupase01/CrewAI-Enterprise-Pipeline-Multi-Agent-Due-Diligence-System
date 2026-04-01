from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from crewai_enterprise_pipeline_api.core.security_utils import hash_client_secret
from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.db.base import Base

_database: "Database | None" = None


class Database:
    def __init__(self, database_url: str, *, echo: bool = False) -> None:
        self.database_url = database_url
        self.engine: AsyncEngine = create_async_engine(database_url, echo=echo)
        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    async def create_schema(self) -> None:
        from crewai_enterprise_pipeline_api.db import models  # noqa: F401

        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await self.ensure_runtime_defaults()

    async def ensure_runtime_defaults(self) -> None:
        from crewai_enterprise_pipeline_api.db.models import (
            ApiClientRecord,
            OrganizationRecord,
            OrgRuntimeConfigRecord,
        )

        settings = get_settings()
        async with self.session_factory() as session:
            session.info["skip_audit"] = True

            organization = await session.get(
                OrganizationRecord,
                settings.default_org_id,
                execution_options={"skip_org_scope": True},
            )
            if organization is None:
                organization = OrganizationRecord(
                    id=settings.default_org_id,
                    name=settings.default_org_name,
                    slug=settings.default_org_slug,
                    status="active",
                )
                session.add(organization)
            else:
                organization.name = settings.default_org_name
                organization.slug = settings.default_org_slug
                organization.status = "active"

            runtime_result = await session.execute(
                select(OrgRuntimeConfigRecord)
                .execution_options(skip_org_scope=True)
                .where(OrgRuntimeConfigRecord.org_id == settings.default_org_id)
            )
            runtime_config = runtime_result.scalar_one_or_none()
            if runtime_config is None:
                runtime_config = OrgRuntimeConfigRecord(
                    org_id=settings.default_org_id,
                    llm_provider=None,
                    llm_model=None,
                )
                session.add(runtime_config)

            result = await session.execute(
                select(ApiClientRecord)
                .execution_options(skip_org_scope=True)
                .where(ApiClientRecord.client_id == settings.default_api_client_id)
            )
            client = result.scalar_one_or_none()
            if client is None:
                client = ApiClientRecord(
                    org_id=settings.default_org_id,
                    client_id=settings.default_api_client_id,
                    display_name=settings.default_api_client_display_name,
                    client_secret_hash=hash_client_secret(settings.default_api_client_secret),
                    role=settings.default_api_client_role,
                    actor_email=settings.default_api_client_email,
                    active=True,
                )
                session.add(client)
            else:
                client.org_id = settings.default_org_id
                client.display_name = settings.default_api_client_display_name
                client.client_secret_hash = hash_client_secret(settings.default_api_client_secret)
                client.role = settings.default_api_client_role
                client.actor_email = settings.default_api_client_email
                client.active = True

            await session.commit()

    async def dispose(self) -> None:
        await self.engine.dispose()

    def session(self) -> AsyncIterator[AsyncSession]:
        return self.session_factory()


def get_database() -> Database:
    global _database

    settings = get_settings()
    if _database is None or _database.database_url != settings.database_url:
        _database = Database(
            settings.database_url,
            echo=settings.app_env == "development",
        )
    return _database


async def close_database() -> None:
    global _database

    if _database is not None:
        await _database.dispose()
        _database = None
