def test_health_endpoint_returns_ok(client) -> None:
    response = client.get("/api/v1/system/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["auth_required"] is False
    assert payload["enabled_motion_packs"] == [
        "buy_side_diligence",
        "credit_lending",
        "vendor_onboarding",
    ]
    assert payload["enabled_sector_packs"] == [
        "tech_saas_services",
        "manufacturing_industrials",
        "bfsi_nbfc",
    ]


def test_overview_endpoint_exposes_pack_strategy(client) -> None:
    response = client.get("/api/v1/system/overview")

    assert response.status_code == 200
    payload = response.json()
    assert "credit_lending" in payload["motion_packs"]
    assert "bfsi_nbfc" in payload["sector_packs"]
    assert payload["auth_required"] is False


def test_readiness_endpoint_reports_component_status(client) -> None:
    response = client.get("/api/v1/system/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    component_names = {component["name"] for component in payload["components"]}
    assert "database" in component_names
    assert "storage" in component_names
