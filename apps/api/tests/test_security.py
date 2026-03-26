import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.db.session import close_database
from crewai_enterprise_pipeline_api.main import create_app


@pytest.fixture
def secured_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    database_path = tmp_path / "phase6-security.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTO_CREATE_SCHEMA", "true")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LOCAL_STORAGE_ROOT", str((tmp_path / "storage").resolve()))
    monkeypatch.setenv("ENFORCE_AUTH", "true")
    get_settings.cache_clear()

    with TestClient(create_app()) as test_client:
        yield test_client

    get_settings.cache_clear()
    asyncio.run(close_database())


def auth_headers(role: str, user_id: str = "phase6-user") -> dict[str, str]:
    return {
        "X-CEP-User-Id": user_id,
        "X-CEP-User-Name": f"{role.title()} User",
        "X-CEP-User-Email": f"{role}@example.com",
        "X-CEP-User-Role": role,
    }


def test_enforced_auth_requires_headers(secured_client: TestClient) -> None:
    response = secured_client.get("/api/v1/cases")

    assert response.status_code == 401


def test_viewer_cannot_create_case_when_auth_is_enforced(
    secured_client: TestClient,
) -> None:
    response = secured_client.post(
        "/api/v1/cases",
        headers=auth_headers("viewer"),
        json={
            "name": "Viewer Attempt",
            "target_name": "Blocked Case",
            "summary": "Viewer should not have write access.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )

    assert response.status_code == 403


def test_reviewer_can_review_after_analyst_creates_case(
    secured_client: TestClient,
) -> None:
    create_response = secured_client.post(
        "/api/v1/cases",
        headers=auth_headers("analyst", user_id="analyst-1"),
        json={
            "name": "Secured Case",
            "target_name": "Role Guard Private Limited",
            "summary": "Reviewer access validation case.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    assert create_response.status_code == 201
    assert create_response.headers["x-request-id"]
    case_id = create_response.json()["id"]

    seed_response = secured_client.post(
        f"/api/v1/cases/{case_id}/checklist/seed",
        headers=auth_headers("analyst", user_id="analyst-1"),
    )
    assert seed_response.status_code == 201

    approval_response = secured_client.post(
        f"/api/v1/cases/{case_id}/approvals/review",
        headers=auth_headers("reviewer", user_id="reviewer-1"),
        json={
            "reviewer": "Review Committee",
            "note": "Role-based review path works.",
        },
    )

    assert approval_response.status_code == 201
    assert approval_response.json()["decision"] == "changes_requested"
