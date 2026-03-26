from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.db.session import get_database


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    database = get_database()
    async with database.session() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db_session)]
