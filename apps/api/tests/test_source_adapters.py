def test_source_adapter_catalog_exposes_phase14_india_connectors(client) -> None:
    response = client.get("/api/v1/source-adapters")

    assert response.status_code == 200
    payload = response.json()
    adapter_keys = {adapter["adapter_key"] for adapter in payload}
    statuses = {adapter["adapter_key"]: adapter["status"] for adapter in payload}

    assert {
        "uploaded_dataroom",
        "mca21",
        "gstin",
        "sebi_scores",
        "roc_filings",
        "cibil",
        "sanctions",
    }.issubset(adapter_keys)
    assert statuses["uploaded_dataroom"] == "available"
    assert statuses["mca21"] == "stub"
    assert statuses["cibil"] == "stub"
