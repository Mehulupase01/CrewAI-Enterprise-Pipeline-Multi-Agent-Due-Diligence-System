from fastapi.testclient import TestClient

from crewai_enterprise_pipeline_api.main import create_app

client = TestClient(create_app())


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/api/v1/system/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["enabled_motion_packs"] == ["buy_side_diligence"]
    assert payload["enabled_sector_packs"] == ["tech_saas_services"]


def test_overview_endpoint_exposes_pack_strategy() -> None:
    response = client.get("/api/v1/system/overview")

    assert response.status_code == 200
    payload = response.json()
    assert "credit_lending" in payload["motion_packs"]
    assert "bfsi_nbfc" in payload["sector_packs"]
