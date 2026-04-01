from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from crewai_enterprise_pipeline_api.core.logging import configure_logging
from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.core.telemetry import initialize_observability
from crewai_enterprise_pipeline_api.db.session import close_database, get_database
from crewai_enterprise_pipeline_api.main import create_app


def test_liveness_endpoint_returns_alive(client: TestClient) -> None:
    response = client.get("/api/v1/health/liveness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "alive"


def test_runtime_readiness_exposes_dependency_probe_details(client: TestClient) -> None:
    response = client.get("/api/v1/health/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    names = {item["name"] for item in payload["dependencies"]}
    assert {"database", "redis", "storage", "openrouter"} <= names
    redis = next(item for item in payload["dependencies"] if item["name"] == "redis")
    assert redis["mode"] in {"live", "disabled"}


def test_metrics_endpoint_exposes_prometheus_series(client: TestClient) -> None:
    response = client.get("/api/v1/metrics")

    assert response.status_code == 200
    assert "cep_http_requests_total" in response.text
    assert "cep_dependency_probe_duration_seconds" in response.text


def test_production_readiness_degrades_when_openrouter_is_enabled_without_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "phase16-production.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTO_CREATE_SCHEMA", "true")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LOCAL_STORAGE_ROOT", str((tmp_path / "storage").resolve()))
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    get_settings.cache_clear()

    with TestClient(create_app()) as production_client:
        response = production_client.get("/api/v1/health/readiness")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "failed"
        openrouter = next(
            item for item in payload["dependencies"] if item["name"] == "openrouter"
        )
        assert openrouter["status"] == "failed"
        assert openrouter["mode"] == "unconfigured"

    get_settings.cache_clear()
    asyncio.run(close_database())


def test_configure_logging_uses_json_renderer_in_production() -> None:
    configure_logging("production")
    handler = logging.getLogger().handlers[0]

    assert handler.formatter is not None
    assert handler.formatter.processors[-1].__class__.__name__ == "JSONRenderer"


def test_tracing_initialization_smoke(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    database_path = tmp_path / "phase16-tracing.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTO_CREATE_SCHEMA", "true")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LOCAL_STORAGE_ROOT", str((tmp_path / "storage").resolve()))
    get_settings.cache_clear()

    app = create_app()
    initialize_observability(settings=get_settings(), app=app, engine=get_database().engine)

    get_settings.cache_clear()
    asyncio.run(close_database())
