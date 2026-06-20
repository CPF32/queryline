"""Tests for persistent chat conversations."""

from __future__ import annotations

import uuid


def _create_data_source(client, sample_sqlite_db) -> str:
    response = client.post(
        "/api/v1/data-sources",
        json={
            "name": f"conv-test-{uuid.uuid4().hex[:8]}",
            "connector_type": "sqlite",
            "connection_config": {"file_path": str(sample_sqlite_db)},
            "is_active": True,
        },
    )
    assert response.status_code == 201
    return response.get_json()["data"]["id"]


def test_conversation_lifecycle(client, sample_sqlite_db):
    data_source_id = _create_data_source(client, sample_sqlite_db)

    created = client.post(
        "/api/v1/conversations",
        json={"data_source_id": data_source_id, "title": "Revenue by region"},
    )
    assert created.status_code == 201
    conversation = created.get_json()["data"]
    conversation_id = conversation["id"]

    appended = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={
            "role": "user",
            "content": "Show revenue by region",
        },
    )
    assert appended.status_code == 201

    listed = client.get(f"/api/v1/conversations/{conversation_id}/messages")
    assert listed.status_code == 200
    messages = listed.get_json()["data"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"

    conversations = client.get(
        f"/api/v1/conversations?data_source_id={data_source_id}",
    )
    assert conversations.status_code == 200
    assert conversations.get_json()["meta"]["total"] == 1

    deleted = client.delete(f"/api/v1/conversations/{conversation_id}")
    assert deleted.status_code == 204


def test_conversation_archive_and_restore(client, sample_sqlite_db):
    data_source_id = _create_data_source(client, sample_sqlite_db)

    created = client.post(
        "/api/v1/conversations",
        json={"data_source_id": data_source_id},
    )
    conversation_id = created.get_json()["data"]["id"]

    archived = client.patch(
        f"/api/v1/conversations/{conversation_id}",
        json={"archived": True},
    )
    assert archived.status_code == 200
    assert archived.get_json()["data"]["archived_at"] is not None

    active = client.get(f"/api/v1/conversations?data_source_id={data_source_id}")
    assert active.get_json()["meta"]["total"] == 0

    archived_list = client.get(
        f"/api/v1/conversations?data_source_id={data_source_id}&archived=true",
    )
    assert archived_list.get_json()["meta"]["total"] == 1

    restored = client.patch(
        f"/api/v1/conversations/{conversation_id}",
        json={"archived": False},
    )
    assert restored.status_code == 200
    assert restored.get_json()["data"]["archived_at"] is None
