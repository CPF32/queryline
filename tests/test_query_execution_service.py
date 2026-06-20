"""Tests for SQL validation, execution wrapper, and orchestration."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from app.adapters.base import QueryColumnMeta, QueryResult
from app.errors import ValidationAppError
from app.services import query_execution_service as qes


KNOWN_TABLES = {"orders", "customers"}
KNOWN_COLUMNS = {
    "orders": {"id", "customer_id", "amount", "client_id"},
    "customers": {"id", "name", "region"},
}


class TestValidateSql:
    def test_valid_select_passes(self) -> None:
        result = qes.validate_sql(
            "SELECT id, client_id FROM orders LIMIT 10",
            "postgres",
            KNOWN_TABLES,
            KNOWN_COLUMNS,
        )
        assert result.valid is True
        assert result.sql is not None
        assert "FROM orders" in result.sql

    def test_drop_table_rejected(self) -> None:
        result = qes.validate_sql(
            "DROP TABLE orders",
            "postgres",
            KNOWN_TABLES,
            KNOWN_COLUMNS,
        )
        assert result.valid is False
        assert result.error_category == "forbidden_statement"
        assert "DROP" in (result.error_message or "")

    def test_hallucinated_column_rejected_with_specific_message(self) -> None:
        result = qes.validate_sql(
            "SELECT cliet_id FROM orders",
            "postgres",
            KNOWN_TABLES,
            KNOWN_COLUMNS,
        )
        assert result.valid is False
        assert result.error_category == "column_not_found"
        assert result.error_message is not None
        assert "cliet_id" in result.error_message
        assert "orders" in result.error_message
        assert "client_id" in result.error_message

    def test_injects_limit_for_postgres(self) -> None:
        result = qes.validate_sql(
            "SELECT id, client_id FROM orders",
            "postgres",
            KNOWN_TABLES,
            KNOWN_COLUMNS,
            max_rows=500,
        )
        assert result.valid is True
        assert result.sql is not None
        assert "LIMIT 500" in result.sql

    def test_injects_top_for_tsql(self) -> None:
        result = qes.validate_sql(
            "SELECT id, client_id FROM orders",
            "tsql",
            KNOWN_TABLES,
            KNOWN_COLUMNS,
            max_rows=250,
        )
        assert result.valid is True
        assert result.sql is not None
        assert "TOP 250" in result.sql

    def test_aggregate_without_group_by_skips_limit(self) -> None:
        result = qes.validate_sql(
            "SELECT COUNT(*) FROM orders",
            "postgres",
            KNOWN_TABLES,
            KNOWN_COLUMNS,
        )
        assert result.valid is True
        assert result.sql is not None
        assert "LIMIT" not in result.sql.upper()

    def test_unknown_table_rejected(self) -> None:
        result = qes.validate_sql(
            "SELECT id FROM invoices",
            "postgres",
            KNOWN_TABLES,
            KNOWN_COLUMNS,
        )
        assert result.valid is False
        assert result.error_category == "table_not_found"


class TestExecuteValidatedQuery:
    def test_classify_timeout_error(self) -> None:
        category, _ = qes.classify_execution_error(TimeoutError("query timed out"))
        assert category == "timeout"

    def test_classify_column_not_found(self) -> None:
        category, _ = qes.classify_execution_error(
            Exception('no such column: "cliet_id"')
        )
        assert category == "column_not_found"

    @patch("app.services.query_execution_service.DataSourceFactory.get_adapter")
    @patch("app.services.query_execution_service.get_data_source_row")
    def test_execute_validated_query_success(
        self,
        mock_get_row,
        mock_get_adapter,
    ) -> None:
        mock_get_row.return_value = type(
            "Row",
            (),
            {
                "id": "00000000-0000-4000-8000-000000000001",
                "name": "Test",
                "connector_type": "sqlite",
                "connection_config": {"file_path": ":memory:"},
                "is_active": True,
                "dialect_name": "sqlite",
                "created_at": "2026-06-19T00:00:00Z",
                "updated_at": "2026-06-19T00:00:00Z",
                "user_id": None,
                "workspace_id": None,
            },
        )()
        adapter = mock_get_adapter.return_value
        adapter.readonly_verified = True
        adapter.execute_readonly_query.return_value = QueryResult(
            columns=[QueryColumnMeta(name="id", type="int")],
            rows=[[1]],
            row_count=1,
            truncated=False,
            execution_ms=12.5,
        )

        result = qes.execute_validated_query(
            "SELECT id FROM orders LIMIT 1",
            "00000000-0000-4000-8000-000000000001",
            max_rows=100,
            timeout_seconds=10,
        )
        assert result.row_count == 1
        adapter.execute_readonly_query.assert_called_once_with(
            "SELECT id FROM orders LIMIT 1",
            max_rows=100,
            timeout_seconds=10,
        )


class TestExecuteQueryIntegration:
    @pytest.fixture()
    def seeded_data_source(self, app, sample_sqlite_db):
        from app.db import DataSourceRow, SchemaColumnRow, SchemaTableRow, db
        from app.util.time import utc_now_iso

        data_source_id = str(uuid.uuid4())
        now = utc_now_iso()
        with app.app_context():
            db.session.add(
                DataSourceRow(
                    id=data_source_id,
                    name="Test SQLite",
                    connector_type="sqlite",
                    connection_config={"file_path": str(sample_sqlite_db)},
                    is_active=True,
                    dialect_name="sqlite",
                    created_at=now,
                    updated_at=now,
                )
            )
            orders_table_id = str(uuid.uuid4())
            customers_table_id = str(uuid.uuid4())
            db.session.add(
                SchemaTableRow(
                    id=orders_table_id,
                    data_source_id=data_source_id,
                    schema_name=None,
                    table_name="orders",
                    display_name=None,
                    description=None,
                    is_included_in_prompt=True,
                    row_count_estimate=2,
                    created_at=now,
                    updated_at=now,
                )
            )
            db.session.add(
                SchemaTableRow(
                    id=customers_table_id,
                    data_source_id=data_source_id,
                    schema_name=None,
                    table_name="customers",
                    display_name=None,
                    description=None,
                    is_included_in_prompt=True,
                    row_count_estimate=2,
                    created_at=now,
                    updated_at=now,
                )
            )
            for table_id, table_name, columns in (
                (
                    orders_table_id,
                    "orders",
                    [
                        ("id", 1),
                        ("customer_id", 2),
                        ("amount", 3),
                        ("client_id", 4),
                    ],
                ),
                (
                    customers_table_id,
                    "customers",
                    [("id", 1), ("name", 2), ("region", 3)],
                ),
            ):
                for column_name, position in columns:
                    db.session.add(
                        SchemaColumnRow(
                            id=str(uuid.uuid4()),
                            table_id=table_id,
                            column_name=column_name,
                            display_name=None,
                            description=None,
                            data_type="TEXT",
                            is_nullable=True,
                            is_primary_key=column_name == "id",
                            ordinal_position=position,
                            sample_distinct_values=None,
                            is_pii=False,
                            is_excluded_from_prompt=False,
                            created_at=now,
                            updated_at=now,
                        )
                    )
            db.session.commit()
        return data_source_id

    def test_execute_query_rejects_invalid_sql(self, app, seeded_data_source) -> None:
        with app.app_context():
            with pytest.raises(ValidationAppError) as exc_info:
                qes.execute_query(
                    data_source_id=seeded_data_source,
                    session_id=str(uuid.uuid4()),
                    sql="DROP TABLE orders",
                    user_question="drop it",
                )
            assert "DROP" in exc_info.value.message

    def test_execute_query_logs_validation_failure(
        self,
        app,
        seeded_data_source,
    ) -> None:
        with app.app_context():
            with pytest.raises(ValidationAppError) as exc_info:
                qes.execute_query(
                    data_source_id=seeded_data_source,
                    session_id=str(uuid.uuid4()),
                    sql="SELECT cliet_id FROM orders",
                    user_question="bad column",
                )
            assert "client_id" in exc_info.value.message

    def test_execute_endpoint_returns_validation_error(self, client, seeded_data_source) -> None:
        response = client.post(
            "/api/v1/chat/execute",
            json={
                "data_source_id": seeded_data_source,
                "session_id": str(uuid.uuid4()),
                "sql": "DROP TABLE orders",
                "user_question": "drop",
            },
        )
        assert response.status_code == 422
        payload = response.get_json()
        assert payload["error"]["code"] == "validation_error"
        assert "DROP" in payload["error"]["message"]


class TestGenerateAndExecute:
    @patch("app.services.query_execution_service.generate_sql")
    def test_orchestration_retries_after_validation_failure(self, mock_generate, app) -> None:
        mock_generate.side_effect = [
            type(
                "Gen",
                (),
                {
                    "success": True,
                    "sql": "SELECT cliet_id FROM orders",
                    "explanation": "first try",
                    "confidence": "medium",
                    "tables_used": ["orders"],
                },
            )(),
            type(
                "Gen",
                (),
                {
                    "success": True,
                    "sql": "SELECT client_id FROM orders LIMIT 10",
                    "explanation": "fixed",
                    "confidence": "high",
                    "tables_used": ["orders"],
                },
            )(),
        ]

        data_source_id = str(uuid.uuid4())
        with app.app_context(), patch.object(
            qes,
            "build_schema_catalog",
            return_value=(KNOWN_TABLES, KNOWN_COLUMNS),
        ), patch.object(
            qes,
            "get_data_source_row",
            return_value=type("Row", (), {"dialect_name": "postgres"})(),
        ), patch.object(
            qes,
            "execute_validated_query",
            return_value=QueryResult(
                columns=[QueryColumnMeta(name="client_id", type="string")],
                rows=[["abc"]],
                row_count=1,
                truncated=False,
                execution_ms=1.0,
            ),
        ), patch.object(qes, "create_query_log_entry") as mock_log:
            mock_log.return_value = type("Log", (), {"id": "log-id"})()
            outcome = qes.generate_and_execute(
                data_source_id=data_source_id,
                session_id=str(uuid.uuid4()),
                question="show client ids",
            )

        assert outcome.success is True
        assert outcome.attempts == 2
        assert mock_generate.call_count == 2
        assert mock_log.call_count == 2
