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
    default_org_id: str = "00000000-0000-0000-0000-000000000001"
    default_org_name: str = "Local Default Organization"
    default_org_slug: str = "local-default"
    default_api_client_id: str = "local-admin-client"
    default_api_client_secret: str = "local-admin-secret"
    default_api_client_display_name: str = "Local Admin Client"
    default_api_client_role: str = "admin"
    default_api_client_email: str = "platform-admin@local.invalid"
    jwt_secret: str = "change-me-in-production-with-32-plus-bytes"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_seconds: int = 3600
    rate_limit_enabled: bool = True
    rate_limit_auth_per_minute: int = 10
    rate_limit_connector_per_minute: int = 30
    rate_limit_mutating_per_minute: int = 120
    rate_limit_read_per_minute: int = 600
    request_id_header_name: str = "X-Request-ID"
    observability_enabled: bool = True
    metrics_enabled: bool = True
    otel_service_name: str = "crewai-enterprise-pipeline-api"
    otel_exporter_otlp_endpoint: str | None = None
    otel_exporter_otlp_insecure: bool = True
    dependency_probe_timeout_seconds: float = 5.0
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
    current_phase: str = "Phase 18 complete: Hardening + Release Packaging"
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
    llm_base_url: str | None = None
    llm_model_catalog_cache_seconds: int = 600
    crew_verbose: bool = False
    crew_max_rpm: int = 10
    crew_tool_top_k: int = 5
    crew_tool_max_usage: int = 6
    source_adapter_force_stub: bool = False
    source_adapter_http_timeout_seconds: float = 10.0
    mca21_api_base_url: str | None = None
    mca21_api_key: str | None = None
    gstin_api_base_url: str | None = None
    gstin_api_key: str | None = None
    sebi_scores_api_base_url: str | None = None
    sebi_scores_api_key: str | None = None
    roc_api_base_url: str | None = None
    roc_api_key: str | None = None
    cibil_api_base_url: str | None = None
    cibil_api_key: str | None = None
    sanctions_ofac_url: str | None = None
    sanctions_mca_url: str | None = None
    sanctions_sebi_url: str | None = None
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

    @property
    def header_auth_allowed(self) -> bool:
        return self.app_env in {"development", "test"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
