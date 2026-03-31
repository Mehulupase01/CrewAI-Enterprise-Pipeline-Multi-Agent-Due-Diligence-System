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
    enforce_auth: bool = False
    default_actor_id: str = "local-operator"
    default_actor_name: str = "Local Operator"
    default_actor_email: str = "local-operator@local.invalid"
    default_actor_role: str = "admin"
    request_id_header_name: str = "X-Request-ID"
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
    product_name: str = "CrewAI Enterprise Pipeline"
    current_phase: str = (
        "Phase 7 complete + post-Phase-7 enhancement: Tool-Grounded CrewAI Evidence Access"
    )
    country: str = "India"
    enabled_motion_packs: str = "buy_side_diligence,credit_lending,vendor_onboarding"
    enabled_sector_packs: str = "tech_saas_services,manufacturing_industrials,bfsi_nbfc"
    worker_concurrency: int = 4
    max_upload_mb: int = 50
    background_mode: bool = False
    embedding_provider: str = "none"  # "none", "openai", "local"
    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: str | None = None
    embedding_dimensions: int = 1536
    llm_provider: str = "none"  # "none", "openai", "anthropic"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    crew_verbose: bool = False
    crew_max_rpm: int = 10
    crew_tool_top_k: int = 5
    crew_tool_max_usage: int = 6
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

    @property
    def auth_required(self) -> bool:
        return self.enforce_auth or self.app_env not in {"development", "test"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
