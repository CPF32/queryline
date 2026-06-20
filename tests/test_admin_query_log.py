"""Integration tests for query log endpoints."""

from __future__ import annotations

from app.services import query_log_service


def test_query_log_filters_and_promote(client, sample_sqlite_db):
    create_source = client.post(
        "/api/admin/data-sources",
        json={
            "name": "Query Log DB",
            "connector_type": "sqlite",
            "connection_config": {"file_path": str(sample_sqlite_db)},
        },
    )
    data_source_id = create_source.get_json()["data"]["id"]

    with client.application.app_context():
        success_entry = query_log_service.create_query_log_entry(
            data_source_id=data_source_id,
            session_id="session-1",
            user_question="Count customers",
            generated_sql="SELECT COUNT(*) FROM customers",
            execution_status="success",
            row_count=1,
            execution_ms=12.5,
        )
        error_entry = query_log_service.create_query_log_entry(
            data_source_id=data_source_id,
            session_id="session-1",
            user_question="Bad query",
            generated_sql="DELETE FROM customers",
            execution_status="execution_error",
            error_message="Only SELECT allowed",
        )

    list_response = client.get(f"/api/admin/query-log?data_source_id={data_source_id}")
    assert list_response.status_code == 200
    assert list_response.get_json()["meta"]["total"] == 2

    success_only = client.get(
        f"/api/admin/query-log?data_source_id={data_source_id}&execution_status=success"
    )
    assert success_only.status_code == 200
    assert success_only.get_json()["meta"]["total"] == 1

    promote_response = client.post(
        f"/api/admin/query-log/{success_entry.id}/promote-to-example",
        json={"notes": "Promoted from chat"},
    )
    assert promote_response.status_code == 201
    example = promote_response.get_json()["data"]
    assert example["question"] == "Count customers"
    assert example["notes"] == "Promoted from chat"

    reject_promote = client.post(
        f"/api/admin/query-log/{error_entry.id}/promote-to-example",
        json={},
    )
    assert reject_promote.status_code == 422
    assert reject_promote.get_json()["error"]["code"] == "validation_error"
