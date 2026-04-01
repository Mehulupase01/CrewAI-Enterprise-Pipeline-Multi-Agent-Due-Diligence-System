from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


def test_dependency_refresh_persists_runtime_statuses(client):
    refresh = client.post("/api/v1/admin/system/dependencies/refresh")
    assert refresh.status_code == 200
    refreshed = refresh.json()
    assert refreshed["dependencies"]

    latest = client.get("/api/v1/system/dependencies")
    assert latest.status_code == 200
    body = latest.json()
    dependency_names = {item["name"] for item in body["dependencies"]}
    assert "database" in dependency_names
    assert "openrouter" in dependency_names


def test_system_llm_default_returns_org_runtime_config(client):
    response = client.get("/api/v1/system/llm/default")
    assert response.status_code == 200
    body = response.json()
    assert body["org_id"] == "00000000-0000-0000-0000-000000000001"
    assert body["llm_provider"] is None
    assert body["llm_model"] is None


def test_admin_openrouter_default_persists_and_queued_run_keeps_effective_runtime(
    client,
    monkeypatch: pytest.MonkeyPatch,
):
    from crewai_enterprise_pipeline_api.core.settings import get_settings
    from crewai_enterprise_pipeline_api.domain.models import LlmModelOption
    from crewai_enterprise_pipeline_api.services.runtime_control_service import (
        RuntimeControlService,
    )

    monkeypatch.setenv("LLM_API_KEY", "phase19-test-key")
    get_settings.cache_clear()

    async def fake_models(self):
        return [
            LlmModelOption(
                model_id="openrouter/test-model",
                label="OpenRouter Test Model",
                provider="openrouter",
                tool_calling_supported=True,
                text_output_supported=True,
                context_length=128000,
                pricing_summary="prompt=0.0 | completion=0.0",
            )
        ]

    monkeypatch.setattr(RuntimeControlService, "_fetch_openrouter_models", fake_models)

    client.app.state.redis_pool = AsyncMock()
    client.app.state.redis_pool.enqueue_job = AsyncMock(return_value=None)

    try:
        update = client.patch(
            "/api/v1/admin/system/llm/default",
            json={
                "llm_provider": "openrouter",
                "llm_model": "openrouter/test-model",
            },
        )
        assert update.status_code == 200
        assert update.json()["llm_provider"] == "openrouter"
        assert update.json()["llm_model"] == "openrouter/test-model"

        case = client.post(
            "/api/v1/cases",
            json={
                "name": "Phase 19 Runtime Queue",
                "target_name": "RuntimeCo",
                "motion_pack": "buy_side_diligence",
                "sector_pack": "tech_saas_services",
            },
        ).json()
        case_id = case["id"]
        client.post(f"/api/v1/cases/{case_id}/checklist/seed")

        run_response = client.post(
            f"/api/v1/cases/{case_id}/runs",
            json={"requested_by": "Runtime Admin"},
        )
        assert run_response.status_code == 201
        run_payload = run_response.json()
        assert run_payload["status"] == "queued"

        list_response = client.get(f"/api/v1/cases/{case_id}/runs")
        assert list_response.status_code == 200
        run_summary = list_response.json()[0]
        assert run_summary["effective_llm_provider"] == "openrouter"
        assert run_summary["effective_llm_model"] == "openrouter/test-model"

        client.app.state.redis_pool.enqueue_job.assert_called_once()
        args = client.app.state.redis_pool.enqueue_job.call_args[0]
        assert args[0] == "run_workflow_job"
        assert args[1] == case_id
        assert args[2] == run_payload["run_id"]
        assert args[3] == "Runtime Admin"
        assert args[5] == "standard"
        assert args[6] == "openrouter"
        assert args[7] == "openrouter/test-model"
    finally:
        client.app.state.redis_pool = None
        get_settings.cache_clear()


def test_explicit_openrouter_override_fails_fast_without_key(
    client,
    monkeypatch: pytest.MonkeyPatch,
):
    from crewai_enterprise_pipeline_api.core.settings import get_settings

    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "none")
    get_settings.cache_clear()

    case = client.post(
        "/api/v1/cases",
        json={
            "name": "Phase 19 Unavailable Runtime",
            "target_name": "BlockedCo",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
        },
    ).json()
    case_id = case["id"]
    client.post(f"/api/v1/cases/{case_id}/checklist/seed")

    response = client.post(
        f"/api/v1/cases/{case_id}/runs",
        json={
            "requested_by": "Analyst",
            "llm_provider_override": "openrouter",
        },
    )
    assert response.status_code == 503
    assert "OpenRouter" in response.text

    get_settings.cache_clear()


@pytest.mark.anyio
async def test_openrouter_catalog_filters_and_caches(
    client,
    monkeypatch: pytest.MonkeyPatch,
):
    from crewai_enterprise_pipeline_api.core.settings import get_settings
    from crewai_enterprise_pipeline_api.db.session import get_database
    from crewai_enterprise_pipeline_api.services import runtime_control_service as runtime_module
    from crewai_enterprise_pipeline_api.services.runtime_control_service import (
        RuntimeControlService,
    )

    monkeypatch.setenv("LLM_API_KEY", "phase19-test-key")
    get_settings.cache_clear()
    runtime_module._OPENROUTER_MEMORY_CACHE = None

    call_count = {"value": 0}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {
                "data": [
                    {
                        "id": "openrouter/tool-text",
                        "name": "Tool Text Model",
                        "supported_parameters": ["tools", "tool_choice"],
                        "context_length": 64000,
                        "pricing": {"prompt": "0.0", "completion": "0.0"},
                    },
                    {
                        "id": "openrouter/image-only",
                        "name": "Image Only Model",
                        "supported_parameters": ["temperature"],
                        "architecture": {"output_modalities": ["image"]},
                    },
                ]
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers=None):
            call_count["value"] += 1
            return FakeResponse()

    async def fake_redis_client(self):
        return None

    monkeypatch.setattr(runtime_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(RuntimeControlService, "_redis_client", fake_redis_client)

    database = get_database()
    async with database.session_factory() as session:
        service = RuntimeControlService(session)
        providers_first = await service.list_llm_providers()
        providers_second = await service.list_llm_providers()

    openrouter = next(item for item in providers_first if item.provider == "openrouter")
    assert openrouter.available is True
    assert len(openrouter.models) == 1
    assert openrouter.models[0].model_id == "openrouter/tool-text"
    assert call_count["value"] == 1
    assert providers_second[1].models[0].model_id == "openrouter/tool-text"

    runtime_module._OPENROUTER_MEMORY_CACHE = None
    get_settings.cache_clear()


def test_worker_settings_registers_dependency_probe_job():
    from crewai_enterprise_pipeline_api.worker import (
        WorkerSettings,
        refresh_dependency_statuses_job,
    )

    assert refresh_dependency_statuses_job in WorkerSettings.functions
    assert WorkerSettings.cron_jobs
