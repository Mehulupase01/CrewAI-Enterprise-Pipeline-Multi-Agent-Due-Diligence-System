from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

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
