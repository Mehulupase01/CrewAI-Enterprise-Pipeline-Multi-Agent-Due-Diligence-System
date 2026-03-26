def test_source_adapter_catalog_exposes_vendor_ready_strategy(client) -> None:
    response = client.get("/api/v1/source-adapters")

    assert response.status_code == 200
    payload = response.json()
    adapter_keys = {adapter["adapter_key"] for adapter in payload}

    assert "uploaded_dataroom" in adapter_keys
    assert "mca_public_records" in adapter_keys
    assert "vendor_connector" in adapter_keys
