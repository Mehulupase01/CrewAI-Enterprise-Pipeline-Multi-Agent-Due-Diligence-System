from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "CrewAI Enterprise Pipeline"
    app_env: str = "development"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    auto_create_schema: bool = True
    default_country: str = "India"
    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "crewai_pipeline"
    postgres_user: str = "crewai"
    postgres_password: str = "crewai"
    redis_host: str = "localhost"
    redis_port: int = 6379
    minio_endpoint: str = "http://localhost:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_bucket_name: str = "crewai-pipeline"
    storage_backend: str = "auto"
    local_storage_root: str = Field(
        default_factory=lambda: str((Path(__file__).resolve().parents[5] / "storage").resolve())
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
