from __future__ import annotations


def _create_case(client) -> str:
    response = client.post(
        "/api/v1/cases",
        json={
            "name": "Phase 14 Connector Validation",
            "target_name": "Horizon Analytics Private Limited",
            "summary": "India connector validation case.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_mca21_connector_fetch_ingests_document_and_chunks(client) -> None:
    case_id = _create_case(client)

    response = client.post(
        f"/api/v1/cases/{case_id}/source-adapters/mca21/fetch",
        json={"identifier": "U72200KA2019PTC123456"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["artifact"]["source_kind"] == "public_registry"
    assert payload["artifact"]["document_kind"] == "mca21_master_data"
    assert payload["chunks_created"] > 0
    assert payload["evidence_items_created"] > 0


def test_gstin_connector_feeds_tax_summary(client) -> None:
    case_id = _create_case(client)

    fetch_response = client.post(
        f"/api/v1/cases/{case_id}/source-adapters/gstin/fetch",
        json={"identifier": "29ABCDE1234F1Z5"},
    )
    assert fetch_response.status_code == 201

    summary_response = client.get(f"/api/v1/cases/{case_id}/tax-summary")
    assert summary_response.status_code == 200
    payload = summary_response.json()
    assert "29ABCDE1234F1Z5" in payload["gstins"]


def test_sanctions_connector_records_known_match(client) -> None:
    case_id = _create_case(client)

    response = client.post(
        f"/api/v1/cases/{case_id}/source-adapters/sanctions/fetch",
        json={"identifier": "Vector Finvest Limited"},
    )

    assert response.status_code == 201
    case_response = client.get(f"/api/v1/cases/{case_id}")
    assert case_response.status_code == 200
    excerpts = [item["excerpt"] for item in case_response.json()["evidence_items"]]
    assert any("SEBI Debarred Entities" in excerpt or "OFAC SDN" in excerpt for excerpt in excerpts)


def test_cibil_connector_uses_vendor_source_kind(client) -> None:
    case_id = _create_case(client)

    response = client.post(
        f"/api/v1/cases/{case_id}/source-adapters/cibil/fetch",
        json={"identifier": "ABCDE1234F"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["artifact"]["source_kind"] == "vendor_connector"
    assert payload["artifact"]["document_kind"] == "cibil_bureau_report"


def test_unknown_source_adapter_returns_not_found(client) -> None:
    case_id = _create_case(client)

    response = client.post(
        f"/api/v1/cases/{case_id}/source-adapters/unknown/fetch",
        json={"identifier": "test"},
    )

    assert response.status_code == 404
