"""End-to-end chat loop tests across database engines.

Proves the adapter abstraction: the same API flow works for SQLite, MSSQL,
and PostgreSQL with only connector_type / dialect_name differing.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from app.clients.claude_client import ClaudeClient
from app.models.chart_spec import ChartSpec, ChartType
from app.schemas.sql_generation import SqlGenerationToolOutput
from app.services import chart_spec_service, sql_generation_service

SESSION_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
QUESTION = "What is total order amount by customer region?"

TABLES_FOR_IMPORT = ["customers", "orders", "products", "order_items"]


def _seed_analytics_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            region TEXT NOT NULL
        );
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL
        );
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        INSERT INTO customers (id, name, region) VALUES
            (1, 'Acme Corp', 'North'),
            (2, 'Beta LLC', 'South'),
            (3, 'Gamma Inc', 'North');
        INSERT INTO products (id, name, category) VALUES
            (1, 'Widget', 'Hardware'),
            (2, 'Service Plan', 'Software');
        INSERT INTO orders (id, customer_id, order_date, amount) VALUES
            (1, 1, '2026-01-15', 150.0),
            (2, 1, '2026-02-10', 75.0),
            (3, 2, '2026-01-20', 200.0),
            (4, 3, '2026-03-01', 50.0);
        INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES
            (1, 1, 1, 2, 50.0),
            (2, 2, 2, 1, 75.0),
            (3, 3, 1, 4, 50.0),
            (4, 4, 2, 1, 50.0);
        """
    )
    conn.commit()
    conn.close()


@pytest.fixture()
def e2e_sqlite_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "e2e_analytics.db"
    _seed_analytics_db(db_path)
    return db_path


def _sqlite_config(db_path: Path) -> dict[str, Any]:
    return {"connector_type": "sqlite", "connection_config": {"file_path": str(db_path)}}


def _postgres_config() -> dict[str, Any] | None:
    required = ("TEST_POSTGRES_HOST", "TEST_POSTGRES_DATABASE", "TEST_POSTGRES_USERNAME")
    if not all(os.environ.get(key) for key in required):
        return None
    return {
        "connector_type": "postgresql",
        "connection_config": {
            "host": os.environ["TEST_POSTGRES_HOST"],
            "port": int(os.environ.get("TEST_POSTGRES_PORT", "5432")),
            "database": os.environ["TEST_POSTGRES_DATABASE"],
            "username": os.environ["TEST_POSTGRES_USERNAME"],
            "password": os.environ.get("TEST_POSTGRES_PASSWORD", ""),
            "ssl_mode": os.environ.get("TEST_POSTGRES_SSL_MODE", "disable"),
        },
    }


def _mssql_config() -> dict[str, Any] | None:
    required = ("TEST_MSSQL_HOST", "TEST_MSSQL_DATABASE")
    if not all(os.environ.get(key) for key in required):
        return None
    return {
        "connector_type": "mssql",
        "connection_config": {
            "host": os.environ["TEST_MSSQL_HOST"],
            "port": int(os.environ.get("TEST_MSSQL_PORT", "1433")),
            "database": os.environ["TEST_MSSQL_DATABASE"],
            "auth_mode": os.environ.get("TEST_MSSQL_AUTH_MODE", "sql"),
            "username": os.environ.get("TEST_MSSQL_USERNAME", ""),
            "password": os.environ.get("TEST_MSSQL_PASSWORD", ""),
            "driver": os.environ.get("TEST_MSSQL_DRIVER", "ODBC Driver 18 for SQL Server"),
            "encrypt": os.environ.get("TEST_MSSQL_ENCRYPT", "yes"),
            "trust_server_certificate": os.environ.get("TEST_MSSQL_TRUST_CERT", "yes"),
        },
    }


def _sql_by_dialect(dialect: str, *, typo_region: bool = False) -> str:
    region_col = "c.regoin" if typo_region else "c.region"
    if dialect == "tsql":
        return (
            f"SELECT TOP 1000 {region_col} AS region, SUM(o.amount) AS total_amount "
            "FROM customers c INNER JOIN orders o ON o.customer_id = c.id "
            "GROUP BY c.region"
        )
    return (
        f"SELECT {region_col} AS region, SUM(o.amount) AS total_amount "
        "FROM customers c INNER JOIN orders o ON o.customer_id = c.id "
        "GROUP BY c.region LIMIT 1000"
    )


@dataclass
class ScriptedClaudeClient(ClaudeClient):
    sql_responses: list[SqlGenerationToolOutput | Exception] = field(default_factory=list)
    chart_spec: ChartSpec | None = None
    sql_calls: int = 0

    def generate_sql_tool_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> SqlGenerationToolOutput:
        self.sql_calls += 1
        if not self.sql_responses:
            raise RuntimeError("No scripted SQL responses remaining.")
        next_item = self.sql_responses.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item

    def generate_chart_spec_tool_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> ChartSpec:
        return self.chart_spec or ChartSpec(
            chart_type=ChartType.BAR,
            x_field="region",
            y_fields=["total_amount"],
            series_field=None,
            aggregation_applied=True,
            title="Total order amount by region",
        )


def _setup_data_source(client, source_config: dict[str, Any], name: str) -> tuple[str, str]:
    response = client.post(
        "/api/v1/data-sources",
        json={
            "name": name,
            "connector_type": source_config["connector_type"],
            "connection_config": source_config["connection_config"],
            "is_active": True,
        },
    )
    assert response.status_code == 201, response.get_json()
    data_source_id = response.get_json()["data"]["id"]
    dialect = response.get_json()["data"]["dialect_name"]

    introspect = client.post(
        f"/api/v1/data-sources/{data_source_id}/schema/introspect",
        json={},
    )
    assert introspect.status_code == 200, introspect.get_json()
    available = {table["table_name"] for table in introspect.get_json()["data"]["tables"]}
    include_tables = [name for name in TABLES_FOR_IMPORT if name in available]
    assert include_tables, f"No expected tables found; available={sorted(available)}"

    import_response = client.post(
        f"/api/v1/data-sources/{data_source_id}/schema/import",
        json={"mode": "merge", "include_tables": include_tables},
    )
    assert import_response.status_code == 200, import_response.get_json()

    for term_body in [
        {
            "term": "Order Amount",
            "definition": "The monetary value of an order stored in orders.amount.",
        },
        {
            "term": "Customer Region",
            "definition": "Geographic sales region on the customers table.",
        },
        {
            "term": "Active Customer",
            "definition": "A customer with at least one order in the last 90 days.",
            "sql_expression": "EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id)",
        },
    ]:
        glossary_response = client.post(
            f"/api/v1/data-sources/{data_source_id}/glossary",
            json=term_body,
        )
        assert glossary_response.status_code == 201

    example_sql = _sql_by_dialect(dialect).replace("TOP 1000 ", "").replace(" LIMIT 1000", "")
    example_response = client.post(
        f"/api/v1/data-sources/{data_source_id}/examples",
        json={
            "question": "Total order amount by region",
            "sql": example_sql,
            "notes": "Join customers to orders and aggregate amount.",
        },
    )
    assert example_response.status_code == 201
    return data_source_id, dialect


def _run_chat_loop(
    client,
    monkeypatch: pytest.MonkeyPatch,
    data_source_id: str,
    dialect: str,
    *,
    sql_responses: list[SqlGenerationToolOutput],
) -> dict[str, Any]:
    mock_client = ScriptedClaudeClient(sql_responses=sql_responses)
    monkeypatch.setattr(sql_generation_service, "_get_claude_client", lambda: mock_client)
    monkeypatch.setattr(chart_spec_service, "get_llm_client", lambda: mock_client)

    generate_response = client.post(
        "/api/v1/chat/generate-sql",
        json={
            "data_source_id": data_source_id,
            "session_id": SESSION_ID,
            "question": QUESTION,
            "conversation_history": [],
        },
    )
    assert generate_response.status_code == 200, generate_response.get_json()
    generated = generate_response.get_json()["data"]
    assert generated["sql"]
    assert generated["confidence"] in {"high", "medium", "low"}

    execute_response = client.post(
        "/api/v1/chat/execute",
        json={
            "data_source_id": data_source_id,
            "session_id": SESSION_ID,
            "sql": generated["sql"],
            "user_question": QUESTION,
            "max_rows": 1000,
            "timeout_seconds": 30,
        },
    )
    assert execute_response.status_code == 200, execute_response.get_json()
    executed = execute_response.get_json()["data"]
    assert executed["query_result"]["row_count"] >= 1
    column_names = {col["name"] for col in executed["query_result"]["columns"]}
    assert "region" in column_names
    assert "total_amount" in column_names

    chart_response = client.post(
        "/api/v1/chat/chart-spec",
        json={
            "data_source_id": data_source_id,
            "session_id": SESSION_ID,
            "user_question": QUESTION,
            "sql": generated["sql"],
            "query_result": executed["query_result"],
            "query_log_id": executed["query_log_id"],
            "chart_hint": generated.get("chart_hint", "bar"),
        },
    )
    assert chart_response.status_code == 200, chart_response.get_json()
    chart_spec = chart_response.get_json()["data"]["chart_spec"]
    assert chart_spec["chart_type"] in {"bar", "line", "table_only", "stat_card"}
    assert chart_spec["title"]

    log_response = client.get(f"/api/v1/query-log/{executed['query_log_id']}")
    assert log_response.status_code == 200
    log_entry = log_response.get_json()["data"]
    assert log_entry["execution_status"] == "success"
    assert log_entry["chart_spec"] is not None

    return {
        "generated": generated,
        "executed": executed,
        "chart_spec": chart_spec,
        "dialect": dialect,
    }


def test_e2e_sqlite_chat_loop(client, e2e_sqlite_db, monkeypatch):
    data_source_id, dialect = _setup_data_source(
        client, _sqlite_config(e2e_sqlite_db), "E2E SQLite"
    )
    assert dialect == "sqlite"

    result = _run_chat_loop(
        client,
        monkeypatch,
        data_source_id,
        dialect,
        sql_responses=[
            SqlGenerationToolOutput(
                sql=_sql_by_dialect(dialect),
                explanation="Totals order amounts grouped by customer region.",
                tables_used=["customers", "orders"],
                chart_hint="bar",
                confidence="high",
            )
        ],
    )
    regions = {row[0] for row in result["executed"]["query_result"]["rows"]}
    assert "North" in regions or "South" in regions


@pytest.mark.skipif(_mssql_config() is None, reason="MSSQL env not configured")
def test_e2e_mssql_chat_loop(client, monkeypatch):
    config = _mssql_config()
    assert config is not None
    data_source_id, dialect = _setup_data_source(client, config, "E2E MSSQL")
    assert dialect == "tsql"

    _run_chat_loop(
        client,
        monkeypatch,
        data_source_id,
        dialect,
        sql_responses=[
            SqlGenerationToolOutput(
                sql=_sql_by_dialect("tsql"),
                explanation="Totals order amounts grouped by customer region.",
                tables_used=["customers", "orders"],
                chart_hint="bar",
                confidence="high",
            )
        ],
    )


@pytest.mark.skipif(_postgres_config() is None, reason="Postgres env not configured")
def test_e2e_postgres_chat_loop(client, monkeypatch):
    config = _postgres_config()
    assert config is not None
    data_source_id, dialect = _setup_data_source(client, config, "E2E Postgres")
    assert dialect == "postgres"

    _run_chat_loop(
        client,
        monkeypatch,
        data_source_id,
        dialect,
        sql_responses=[
            SqlGenerationToolOutput(
                sql=_sql_by_dialect("postgres"),
                explanation="Totals order amounts grouped by customer region.",
                tables_used=["customers", "orders"],
                chart_hint="bar",
                confidence="high",
            )
        ],
    )


def test_negative_hallucinated_column_recovers_on_retry(
    client, e2e_sqlite_db, monkeypatch
):
    data_source_id, dialect = _setup_data_source(
        client, _sqlite_config(e2e_sqlite_db), "Retry SQLite"
    )

    bad_sql = _sql_by_dialect(dialect, typo_region=True)
    good_sql = _sql_by_dialect(dialect)

    mock_client = ScriptedClaudeClient(
        sql_responses=[
            SqlGenerationToolOutput(
                sql=bad_sql,
                explanation="First attempt with typo.",
                tables_used=["customers", "orders"],
                chart_hint="bar",
                confidence="medium",
            ),
            SqlGenerationToolOutput(
                sql=good_sql,
                explanation="Corrected region column spelling.",
                tables_used=["customers", "orders"],
                chart_hint="bar",
                confidence="high",
            ),
        ]
    )
    monkeypatch.setattr(sql_generation_service, "_get_claude_client", lambda: mock_client)

    first_generate = client.post(
        "/api/v1/chat/generate-sql",
        json={
            "data_source_id": data_source_id,
            "session_id": SESSION_ID,
            "question": QUESTION,
            "conversation_history": [],
        },
    )
    assert first_generate.status_code == 200
    first_sql = first_generate.get_json()["data"]["sql"]

    first_execute = client.post(
        "/api/v1/chat/execute",
        json={
            "data_source_id": data_source_id,
            "session_id": SESSION_ID,
            "sql": first_sql,
            "user_question": QUESTION,
        },
    )
    assert first_execute.status_code == 422
    error_body = first_execute.get_json()["error"]
    assert error_body["code"] in {"validation_error", "sql_generation_failed"}
    assert "query_log_id" in (error_body.get("details") or {})

    retry_generate = client.post(
        "/api/v1/chat/generate-sql",
        json={
            "data_source_id": data_source_id,
            "session_id": SESSION_ID,
            "question": QUESTION,
            "conversation_history": [],
            "retry_context": {
                "previous_sql": first_sql,
                "execution_error": error_body["message"],
                "attempt_number": 2,
            },
        },
    )
    assert retry_generate.status_code == 200
    corrected_sql = retry_generate.get_json()["data"]["sql"]
    assert "regoin" not in corrected_sql.lower()

    second_execute = client.post(
        "/api/v1/chat/execute",
        json={
            "data_source_id": data_source_id,
            "session_id": SESSION_ID,
            "sql": corrected_sql,
            "user_question": QUESTION,
        },
    )
    assert second_execute.status_code == 200
    assert second_execute.get_json()["data"]["query_result"]["row_count"] >= 1


def test_negative_unmapped_question_returns_clean_failure(
    client, e2e_sqlite_db, monkeypatch
):
    data_source_id, _dialect = _setup_data_source(
        client, _sqlite_config(e2e_sqlite_db), "Unmapped SQLite"
    )

    class FailingClient(ClaudeClient):
        def generate_sql_tool_output(self, *, system_prompt: str, user_prompt: str):
            raise RuntimeError("No schema mapping for interplanetary weather.")

        def generate_chart_spec_tool_output(self, *, system_prompt: str, user_prompt: str):
            raise RuntimeError("unused")

    monkeypatch.setattr(sql_generation_service, "_get_claude_client", lambda: FailingClient())

    response = client.post(
        "/api/v1/chat/generate-sql",
        json={
            "data_source_id": data_source_id,
            "session_id": str(uuid.uuid4()),
            "question": "What is the weather forecast on Mars next week?",
            "conversation_history": [],
        },
    )
    assert response.status_code == 422
    error = response.get_json()["error"]
    assert error["code"] == "sql_generation_failed"
    assert error["message"]
    assert "interplanetary" in error["message"] or "schema" in error["message"].lower()


def test_negative_rejects_unsafe_sql(client, e2e_sqlite_db):
    data_source_id, _dialect = _setup_data_source(
        client, _sqlite_config(e2e_sqlite_db), "Unsafe SQLite"
    )

    response = client.post(
        "/api/v1/chat/execute",
        json={
            "data_source_id": data_source_id,
            "session_id": SESSION_ID,
            "sql": "DROP TABLE customers",
            "user_question": "Delete everything",
        },
    )
    assert response.status_code == 422
    error = response.get_json()["error"]
    assert error["code"] == "validation_error"
    assert "read-only" in error["message"].lower() or "SELECT" in error["message"]
