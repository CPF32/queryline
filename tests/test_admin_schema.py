"""Integration tests for schema import and metadata endpoints."""

from __future__ import annotations


def _create_sqlite_source(client, sample_sqlite_db) -> str:
    response = client.post(
        "/api/admin/data-sources",
        json={
            "name": "Schema DB",
            "connector_type": "sqlite",
            "connection_config": {"file_path": str(sample_sqlite_db)},
        },
    )
    assert response.status_code == 201
    return response.get_json()["data"]["id"]


def test_import_schema_returns_snapshot_without_persisting(client, sample_sqlite_db):
    data_source_id = _create_sqlite_source(client, sample_sqlite_db)

    import_response = client.post(f"/api/admin/data-sources/{data_source_id}/import-schema")
    assert import_response.status_code == 200
    tables = import_response.get_json()["data"]["tables"]
    table_names = {table["table_name"] for table in tables}
    assert {"customers", "orders"}.issubset(table_names)

    list_tables_response = client.get(
        f"/api/admin/data-sources/{data_source_id}/schema/tables"
    )
    assert list_tables_response.status_code == 200
    assert list_tables_response.get_json()["meta"]["total"] == 0


def test_onboard_tables_and_metadata_bundle(client, sample_sqlite_db):
    data_source_id = _create_sqlite_source(client, sample_sqlite_db)

    onboard_response = client.post(
        f"/api/admin/data-sources/{data_source_id}/schema-tables",
        json={"tables": [{"table_name": "customers"}, {"table_name": "orders"}]},
    )
    assert onboard_response.status_code == 200
    imported = onboard_response.get_json()["data"]
    assert imported["tables_imported"] == 2
    assert imported["columns_imported"] >= 3

    tables_response = client.get(f"/api/admin/data-sources/{data_source_id}/schema/tables")
    tables = tables_response.get_json()["data"]
    customers = next(table for table in tables if table["table_name"] == "customers")
    table_id = customers["id"]

    update_table_response = client.put(
        f"/api/admin/data-sources/{data_source_id}/schema/tables/{table_id}",
        json={
            "description": "Customer dimension table",
            "display_name": "Customers",
        },
    )
    assert update_table_response.status_code == 200

    columns_response = client.get(
        f"/api/admin/data-sources/{data_source_id}/schema/tables/{table_id}/columns"
    )
    region_column = next(
        column for column in columns_response.get_json()["data"] if column["column_name"] == "region"
    )
    update_column_response = client.put(
        f"/api/admin/data-sources/{data_source_id}/schema/columns/{region_column['id']}",
        json={"is_pii": False, "description": "Sales region"},
    )
    assert update_column_response.status_code == 200

    glossary_response = client.post(
        f"/api/admin/data-sources/{data_source_id}/glossary",
        json={
            "term": "Customer",
            "definition": "An organization that places orders.",
            "table_id": table_id,
        },
    )
    assert glossary_response.status_code == 201

    example_response = client.post(
        f"/api/admin/data-sources/{data_source_id}/examples",
        json={
            "question": "How many customers are there?",
            "sql": "SELECT COUNT(*) FROM customers",
        },
    )
    assert example_response.status_code == 201

    bundle_response = client.get(
        f"/api/admin/data-sources/{data_source_id}/metadata-bundle"
    )
    assert bundle_response.status_code == 200
    bundle = bundle_response.get_json()["data"]
    assert bundle["dialect_name"] == "sqlite"
    assert len(bundle["tables"]) == 2
    assert bundle["tables"][0]["columns"]
    assert bundle["glossary"][0]["table_name"] == "customers"
    assert bundle["examples"][0]["sql"].startswith("SELECT")


def test_manual_relationship_crud(client, sample_sqlite_db):
    data_source_id = _create_sqlite_source(client, sample_sqlite_db)
    client.post(
        f"/api/admin/data-sources/{data_source_id}/schema-tables",
        json={"tables": [{"table_name": "customers"}, {"table_name": "orders"}]},
    )

    tables = client.get(f"/api/admin/data-sources/{data_source_id}/schema/tables").get_json()["data"]
    orders = next(table for table in tables if table["table_name"] == "orders")
    customers = next(table for table in tables if table["table_name"] == "customers")

    order_columns = client.get(
        f"/api/admin/data-sources/{data_source_id}/schema/tables/{orders['id']}/columns"
    ).get_json()["data"]
    customer_columns = client.get(
        f"/api/admin/data-sources/{data_source_id}/schema/tables/{customers['id']}/columns"
    ).get_json()["data"]

    create_rel = client.post(
        f"/api/admin/data-sources/{data_source_id}/schema/relationships",
        json={
            "constraint_name": "manual_orders_customers",
            "source_table_id": orders["id"],
            "source_column_id": next(c["id"] for c in order_columns if c["column_name"] == "customer_id"),
            "target_table_id": customers["id"],
            "target_column_id": next(c["id"] for c in customer_columns if c["column_name"] == "id"),
        },
    )
    assert create_rel.status_code == 201

    relationships = client.get(
        f"/api/admin/data-sources/{data_source_id}/schema/relationships"
    ).get_json()["data"]
    assert len(relationships) == 1

    delete_rel = client.delete(
        f"/api/admin/data-sources/{data_source_id}/schema/relationships/{relationships[0]['id']}"
    )
    assert delete_rel.status_code == 204
