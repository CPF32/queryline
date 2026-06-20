"""Integration tests for admin data source endpoints."""

from __future__ import annotations


def test_list_connectors(client):
    response = client.get("/api/admin/connectors")
    assert response.status_code == 200
    payload = response.get_json()
    connector_types = {item["connector_type"] for item in payload["data"]}
    assert "sqlite" in connector_types


def test_create_data_source_rejects_bad_connection(client):
    response = client.post(
        "/api/admin/data-sources",
        json={
            "name": "Broken",
            "connector_type": "sqlite",
            "connection_config": {"file_path": "/does/not/exist.db"},
        },
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "connection_failed"


def test_data_source_lifecycle(client, sample_sqlite_db):
    create_response = client.post(
        "/api/admin/data-sources",
        json={
            "name": "Local SQLite",
            "engine_type": "sqlite",
            "connection_config": {"file_path": str(sample_sqlite_db)},
        },
    )
    assert create_response.status_code == 201
    created = create_response.get_json()["data"]
    data_source_id = created["id"]
    assert created["dialect_name"] == "sqlite"
    assert created["connection_config"]["file_path"] == str(sample_sqlite_db)

    list_response = client.get("/api/admin/data-sources")
    assert list_response.status_code == 200
    assert list_response.get_json()["meta"]["total"] == 1

    get_response = client.get(f"/api/admin/data-sources/{data_source_id}")
    assert get_response.status_code == 200

    test_response = client.post(f"/api/admin/data-sources/{data_source_id}/test")
    assert test_response.status_code == 200
    assert test_response.get_json()["data"]["success"] is True

    schema_response = client.get(
        f"/api/admin/data-sources/{data_source_id}/connection-form-schema"
    )
    assert schema_response.status_code == 200
    assert "file_path" in schema_response.get_json()["data"]["properties"]

    update_response = client.put(
        f"/api/admin/data-sources/{data_source_id}",
        json={"name": "Renamed SQLite"},
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["data"]["name"] == "Renamed SQLite"

    delete_response = client.delete(f"/api/admin/data-sources/{data_source_id}")
    assert delete_response.status_code == 204
