"""Phase 3 tests: Infrastructure Wiring — Alembic, arq worker, SSE, enqueue fallback."""

from unittest.mock import AsyncMock

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def test_settings_new_fields(client):
    """Phase 3 settings (worker_concurrency, max_upload_mb, background_mode) are present."""
    from crewai_enterprise_pipeline_api.core.settings import get_settings

    s = get_settings()
    assert s.worker_concurrency == 4
    assert s.max_upload_mb == 50
    assert s.background_mode is False


# ---------------------------------------------------------------------------
# Alembic
# ---------------------------------------------------------------------------


def test_alembic_initial_migration_importable():
    """The initial Alembic migration can be imported and has upgrade/downgrade."""
    from pathlib import Path

    migration_path = (
        Path(__file__).resolve().parents[1] / "alembic" / "versions" / "001_initial_schema.py"
    )
    assert migration_path.exists(), f"Migration file not found: {migration_path}"
    text = migration_path.read_text()
    assert 'revision: str = "001"' in text
    assert "def upgrade()" in text
    assert "def downgrade()" in text
    assert "create_table" in text
    assert '"cases"' in text


def test_alembic_env_importable():
    """The Alembic env.py exists and references our Base metadata."""
    from pathlib import Path

    env_path = Path(__file__).resolve().parents[1] / "alembic" / "env.py"
    assert env_path.exists()
    text = env_path.read_text()
    assert "target_metadata = Base.metadata" in text
    assert "run_async_migrations" in text


# ---------------------------------------------------------------------------
# Worker module
# ---------------------------------------------------------------------------


def test_worker_module_importable():
    """The arq worker module can be imported and exposes WorkerSettings."""
    from crewai_enterprise_pipeline_api.worker import WorkerSettings, run_workflow_job

    assert hasattr(WorkerSettings, "functions")
    assert run_workflow_job in WorkerSettings.functions
    assert WorkerSettings.on_startup is not None
    assert WorkerSettings.on_shutdown is not None


# ---------------------------------------------------------------------------
# Sync fallback — POST /runs still works without Redis
# ---------------------------------------------------------------------------


def test_run_sync_fallback(client):
    """POST /runs falls back to synchronous execution when redis_pool is None."""
    # Create a case + seed checklist (required for run)
    case = client.post(
        "/api/v1/cases",
        json={
            "name": "Phase 3 Sync Test",
            "target_name": "TestCo",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
        },
    ).json()
    case_id = case["id"]
    client.post(f"/api/v1/cases/{case_id}/checklist/seed")

    # Execute run — should succeed synchronously (no Redis in test)
    resp = client.post(
        f"/api/v1/cases/{case_id}/runs",
        json={"requested_by": "TestOp"},
    )
    assert resp.status_code == 201
    body = resp.json()
    # Sync path returns WorkflowRunResult with 'run' and 'executive_memo'
    assert "run" in body
    assert "executive_memo" in body
    assert body["run"]["status"] == "completed"


# ---------------------------------------------------------------------------
# Enqueue path — mocked Redis pool
# ---------------------------------------------------------------------------


def test_run_enqueue_with_redis(client):
    """POST /runs enqueues when redis_pool is present on app.state."""
    case = client.post(
        "/api/v1/cases",
        json={
            "name": "Phase 3 Enqueue Test",
            "target_name": "TestCo",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
        },
    ).json()
    case_id = case["id"]
    client.post(f"/api/v1/cases/{case_id}/checklist/seed")

    mock_pool = AsyncMock()
    mock_pool.enqueue_job = AsyncMock(return_value=None)
    client.app.state.redis_pool = mock_pool

    try:
        resp = client.post(
            f"/api/v1/cases/{case_id}/runs",
            json={"requested_by": "TestOp"},
        )
        assert resp.status_code == 201
        body = resp.json()
        # Enqueue path returns WorkflowRunEnqueueResult
        assert "run_id" in body
        assert body["status"] == "queued"
        assert body["case_id"] == case_id
        assert "message" in body

        # Verify arq enqueue was called
        mock_pool.enqueue_job.assert_called_once()
        call_args = mock_pool.enqueue_job.call_args
        assert call_args[0][0] == "run_workflow_job"
        assert call_args[0][1] == case_id
    finally:
        client.app.state.redis_pool = None


# ---------------------------------------------------------------------------
# SSE stream endpoint
# ---------------------------------------------------------------------------


def test_sse_stream_completed_run(client):
    """GET /runs/{id}/stream returns SSE events for a completed run."""
    case = client.post(
        "/api/v1/cases",
        json={
            "name": "Phase 3 SSE Test",
            "target_name": "TestCo",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
        },
    ).json()
    case_id = case["id"]
    client.post(f"/api/v1/cases/{case_id}/checklist/seed")

    run_resp = client.post(
        f"/api/v1/cases/{case_id}/runs",
        json={"requested_by": "TestOp"},
    )
    run_id = run_resp.json()["run"]["id"]

    # Stream the already-completed run
    with client.stream("GET", f"/api/v1/cases/{case_id}/runs/{run_id}/stream") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        text = response.read().decode()
        assert "event: status" in text
        assert "data: completed" in text
        assert "event: trace" in text
        assert "event: done" in text


def test_sse_stream_not_found(client):
    """GET /runs/{id}/stream returns error event for non-existent run."""
    case = client.post(
        "/api/v1/cases",
        json={
            "name": "SSE 404 Test",
            "target_name": "TestCo",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
        },
    ).json()
    case_id = case["id"]

    with client.stream(
        "GET", f"/api/v1/cases/{case_id}/runs/nonexistent-run-id/stream"
    ) as response:
        assert response.status_code == 200
        text = response.read().decode()
        assert "event: error" in text


# ---------------------------------------------------------------------------
# Enqueue result schema
# ---------------------------------------------------------------------------


def test_workflow_run_enqueue_result_schema():
    """WorkflowRunEnqueueResult has the expected fields and defaults."""
    from crewai_enterprise_pipeline_api.domain.models import (
        WorkflowRunEnqueueResult,
        WorkflowRunStatus,
    )

    result = WorkflowRunEnqueueResult(run_id="test-id", case_id="case-id")
    assert result.status == WorkflowRunStatus.QUEUED
    assert "enqueued" in result.message.lower()
