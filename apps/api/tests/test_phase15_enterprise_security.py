import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from crewai_enterprise_pipeline_api.core.security_utils import hash_client_secret
from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.db.models import ApiClientRecord, OrganizationRecord
from crewai_enterprise_pipeline_api.db.session import close_database, get_database
from crewai_enterprise_pipeline_api.main import create_app


@pytest.fixture
def production_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    database_path = tmp_path / "phase15-security.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTO_CREATE_SCHEMA", "true")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LOCAL_STORAGE_ROOT", str((tmp_path / "storage").resolve()))
    monkeypatch.setenv("JWT_SECRET", "phase15-secret")
    get_settings.cache_clear()

    with TestClient(create_app()) as test_client:
        yield test_client

    get_settings.cache_clear()
    asyncio.run(close_database())


@pytest.fixture
def rate_limited_production_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> TestClient:
    database_path = tmp_path / "phase15-rate-limit.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTO_CREATE_SCHEMA", "true")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LOCAL_STORAGE_ROOT", str((tmp_path / "storage").resolve()))
    monkeypatch.setenv("JWT_SECRET", "phase15-secret")
    monkeypatch.setenv("RATE_LIMIT_AUTH_PER_MINUTE", "1")
    get_settings.cache_clear()

    with TestClient(create_app()) as test_client:
        yield test_client

    get_settings.cache_clear()
    asyncio.run(close_database())


def _issue_token(
    client: TestClient,
    *,
    client_id: str = "local-admin-client",
    client_secret: str = "local-admin-secret",
) -> str:
    response = client.post(
        "/api/v1/auth/token",
        json={"client_id": client_id, "client_secret": client_secret},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _seed_api_client(
    *,
    org_id: str,
    org_name: str,
    org_slug: str,
    client_id: str,
    client_secret: str,
    role: str,
    actor_email: str,
) -> None:
    database = get_database()
    async with database.session_factory() as session:
        session.info["skip_audit"] = True
        organization = await session.get(
            OrganizationRecord,
            org_id,
            execution_options={"skip_org_scope": True},
        )
        if organization is None:
            session.add(
                OrganizationRecord(
                    id=org_id,
                    name=org_name,
                    slug=org_slug,
                    status="active",
                )
            )
        session.add(
            ApiClientRecord(
                org_id=org_id,
                client_id=client_id,
                display_name=client_id,
                client_secret_hash=hash_client_secret(client_secret),
                role=role,
                actor_email=actor_email,
                active=True,
            )
        )
        await session.commit()


def test_jwt_token_issuance_and_protected_route_work_in_production(
    production_client: TestClient,
) -> None:
    token = _issue_token(production_client)

    create_response = production_client.post(
        "/api/v1/cases",
        headers=_bearer(token),
        json={
            "name": "JWT Secured Case",
            "target_name": "Secure Target Private Limited",
            "summary": "Production-mode JWT protection works.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )

    assert create_response.status_code == 201, create_response.text
    list_response = production_client.get("/api/v1/cases", headers=_bearer(token))
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_invalid_bearer_token_is_rejected_in_production(
    production_client: TestClient,
) -> None:
    response = production_client.get(
        "/api/v1/cases",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_cross_org_isolation_applies_to_reads_and_writes(
    production_client: TestClient,
) -> None:
    asyncio.run(
        _seed_api_client(
            org_id="00000000-0000-0000-0000-000000000010",
            org_name="Org One",
            org_slug="org-one",
            client_id="org-one-analyst",
            client_secret="org-one-secret",
            role="analyst",
            actor_email="org-one@example.com",
        )
    )
    asyncio.run(
        _seed_api_client(
            org_id="00000000-0000-0000-0000-000000000020",
            org_name="Org Two",
            org_slug="org-two",
            client_id="org-two-analyst",
            client_secret="org-two-secret",
            role="analyst",
            actor_email="org-two@example.com",
        )
    )

    org_one_token = _issue_token(
        production_client,
        client_id="org-one-analyst",
        client_secret="org-one-secret",
    )
    org_two_token = _issue_token(
        production_client,
        client_id="org-two-analyst",
        client_secret="org-two-secret",
    )

    create_response = production_client.post(
        "/api/v1/cases",
        headers=_bearer(org_one_token),
        json={
            "name": "Org One Confidential Case",
            "target_name": "Org One Target",
            "summary": "Org One should own this case.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    assert create_response.status_code == 201, create_response.text
    case_id = create_response.json()["id"]

    list_response = production_client.get("/api/v1/cases", headers=_bearer(org_two_token))
    assert list_response.status_code == 200
    assert list_response.json() == []

    get_response = production_client.get(
        f"/api/v1/cases/{case_id}",
        headers=_bearer(org_two_token),
    )
    assert get_response.status_code == 404

    update_response = production_client.patch(
        f"/api/v1/cases/{case_id}",
        headers=_bearer(org_two_token),
        json={"summary": "Org Two should not update this."},
    )
    assert update_response.status_code == 404


def test_audit_log_captures_mutations_and_authorization_failures(
    production_client: TestClient,
) -> None:
    asyncio.run(
        _seed_api_client(
            org_id="00000000-0000-0000-0000-000000000001",
            org_name="Local Default Organization",
            org_slug="local-default",
            client_id="viewer-client",
            client_secret="viewer-secret",
            role="viewer",
            actor_email="viewer@example.com",
        )
    )

    admin_token = _issue_token(production_client)
    viewer_token = _issue_token(
        production_client,
        client_id="viewer-client",
        client_secret="viewer-secret",
    )

    create_response = production_client.post(
        "/api/v1/cases",
        headers=_bearer(admin_token),
        json={
            "name": "Audited Mutation Case",
            "target_name": "Audit Target",
            "summary": "Mutation should create an audit record.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    assert create_response.status_code == 201, create_response.text

    forbidden_response = production_client.post(
        "/api/v1/cases",
        headers=_bearer(viewer_token),
        json={
            "name": "Blocked Viewer Case",
            "target_name": "No Access",
            "summary": "Viewer write should be forbidden.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    assert forbidden_response.status_code == 403

    audit_response = production_client.get(
        "/api/v1/admin/audit-log",
        headers=_bearer(admin_token),
    )
    assert audit_response.status_code == 200, audit_response.text
    actions = {item["action"] for item in audit_response.json()["items"]}
    assert "CREATE" in actions
    assert "AUTHZ_FAILURE" in actions
    assert "AUTH_TOKEN_ISSUED" in actions


def test_auth_rate_limit_is_enforced(
    rate_limited_production_client: TestClient,
) -> None:
    first = rate_limited_production_client.post(
        "/api/v1/auth/token",
        json={"client_id": "local-admin-client", "client_secret": "local-admin-secret"},
    )
    second = rate_limited_production_client.post(
        "/api/v1/auth/token",
        json={"client_id": "local-admin-client", "client_secret": "local-admin-secret"},
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 429
