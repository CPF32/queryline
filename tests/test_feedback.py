"""Tests for query feedback and learning loop."""

from __future__ import annotations

import uuid

from app.db import SqlExampleRow
from app.services.query_log_service import create_query_log_entry


def _create_data_source(client, sample_sqlite_db) -> str:
    response = client.post(
        "/api/v1/data-sources",
        json={
            "name": f"feedback-test-{uuid.uuid4().hex[:8]}",
            "connector_type": "sqlite",
            "connection_config": {"file_path": str(sample_sqlite_db)},
            "is_active": True,
        },
    )
    assert response.status_code == 201
    return response.get_json()["data"]["id"]


def test_positive_feedback_promotes_example(client, app, sample_sqlite_db):
    data_source_id = _create_data_source(client, sample_sqlite_db)

    with app.app_context():
        entry = create_query_log_entry(
            data_source_id=data_source_id,
            session_id="sess-1",
            user_question="Total sales by month",
            generated_sql="SELECT month, SUM(amount) AS total FROM sales GROUP BY month",
            execution_status="success",
            row_count=12,
            execution_ms=4.2,
        )

    response = client.post(
        f"/api/v1/query-log/{entry.id}/feedback",
        json={"rating": "up"},
    )
    assert response.status_code == 201
    assert response.get_json()["data"]["rating"] == "up"

    with app.app_context():
        examples = SqlExampleRow.query.filter_by(data_source_id=data_source_id).all()
        assert len(examples) == 1
        assert examples[0].source == "feedback"
        assert examples[0].question == "Total sales by month"


def test_negative_feedback_context(client, app, sample_sqlite_db):
    from app.services.feedback_service import get_negative_feedback_context

    data_source_id = _create_data_source(client, sample_sqlite_db)

    with app.app_context():
        entry = create_query_log_entry(
            data_source_id=data_source_id,
            session_id="sess-2",
            user_question="Revenue by customer region",
            generated_sql="SELECT region, SUM(amount) FROM orders GROUP BY region",
            execution_status="success",
        )
        client.post(
            f"/api/v1/query-log/{entry.id}/feedback",
            json={"rating": "down", "comment": "Should group by customer region, not order region"},
        )

    with app.app_context():
        context = get_negative_feedback_context(
            data_source_id,
            "Show revenue grouped by customer region",
        )
        assert len(context) == 1
        assert "customer region" in context[0]["question"].lower()
