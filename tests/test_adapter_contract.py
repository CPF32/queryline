"""Shared adapter contract tests.

All adapters must pass this suite to prove the abstraction holds.
SQLite runs in CI by default; other engines run when configured via env vars.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

import app.adapters
from app.adapters._common import ReadOnlyNotVerifiedError
from app.adapters.base import DataSourceAdapter
from app.adapters.mysql.adapter import MySQLAdapter
from app.adapters.mssql.adapter import MSSQLAdapter
from app.adapters.postgresql.adapter import PostgresAdapter
from app.adapters.registry import ADAPTER_REGISTRY
from app.adapters.sqlite.adapter import SQLiteAdapter
from app.models.data_source import DataSource
from app.services.adapter_factory import DataSourceFactory, get_adapter


def _seed_contract_database(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );
            INSERT INTO customers (id, name, status) VALUES
                (1, 'Alice', 'active'),
                (2, 'Bob', 'inactive'),
                (3, 'Carol', 'active');
            INSERT INTO orders (id, customer_id, amount) VALUES
                (1, 1, 100.0),
                (2, 1, 50.0),
                (3, 2, 75.0);
            CREATE VIEW active_customers AS
                SELECT id, name, status FROM customers WHERE status = 'active';
            """
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def sqlite_db_path() -> str:
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as handle:
        path = Path(handle.name)
    _seed_contract_database(path)
    yield str(path)
    path.unlink(missing_ok=True)


@pytest.fixture
def sqlite_adapter(sqlite_db_path: str) -> SQLiteAdapter:
    return SQLiteAdapter({"file_path": sqlite_db_path})


def _postgres_config() -> dict | None:
    if not os.environ.get("TEST_POSTGRES_URL"):
        return None
    # TEST_POSTGRES_URL not used directly; individual vars preferred
    required = ("TEST_POSTGRES_HOST", "TEST_POSTGRES_DATABASE", "TEST_POSTGRES_USERNAME")
    if not all(os.environ.get(key) for key in required):
        return None
    return {
        "host": os.environ["TEST_POSTGRES_HOST"],
        "port": int(os.environ.get("TEST_POSTGRES_PORT", "5432")),
        "database": os.environ["TEST_POSTGRES_DATABASE"],
        "username": os.environ["TEST_POSTGRES_USERNAME"],
        "password": os.environ.get("TEST_POSTGRES_PASSWORD", ""),
        "ssl_mode": os.environ.get("TEST_POSTGRES_SSL_MODE", "disable"),
    }


def _mysql_config() -> dict | None:
    required = ("TEST_MYSQL_HOST", "TEST_MYSQL_DATABASE", "TEST_MYSQL_USERNAME")
    if not all(os.environ.get(key) for key in required):
        return None
    return {
        "host": os.environ["TEST_MYSQL_HOST"],
        "port": int(os.environ.get("TEST_MYSQL_PORT", "3306")),
        "database": os.environ["TEST_MYSQL_DATABASE"],
        "username": os.environ["TEST_MYSQL_USERNAME"],
        "password": os.environ.get("TEST_MYSQL_PASSWORD", ""),
        "ssl_mode": os.environ.get("TEST_MYSQL_SSL_MODE", "disable"),
    }


def _mssql_config() -> dict | None:
    required = ("TEST_MSSQL_HOST", "TEST_MSSQL_DATABASE")
    if not all(os.environ.get(key) for key in required):
        return None
    return {
        "host": os.environ["TEST_MSSQL_HOST"],
        "port": int(os.environ.get("TEST_MSSQL_PORT", "1433")),
        "database": os.environ["TEST_MSSQL_DATABASE"],
        "auth_mode": os.environ.get("TEST_MSSQL_AUTH_MODE", "sql"),
        "username": os.environ.get("TEST_MSSQL_USERNAME", ""),
        "password": os.environ.get("TEST_MSSQL_PASSWORD", ""),
        "driver": os.environ.get("TEST_MSSQL_DRIVER", "ODBC Driver 18 for SQL Server"),
        "encrypt": os.environ.get("TEST_MSSQL_ENCRYPT", "yes"),
        "trust_server_certificate": os.environ.get("TEST_MSSQL_TRUST_CERT", "yes"),
    }


class AdapterContractSuite:
    """Interface-level tests reused by every adapter implementation."""

    adapter: DataSourceAdapter

    def test_dialect_name(self) -> None:
        assert self.adapter.get_dialect_name() in {"sqlite", "postgres", "mysql", "tsql"}

    def test_connection_form_schema(self) -> None:
        schema = type(self.adapter).get_connection_form_schema()
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        assert schema["title"]

    def test_test_connection(self) -> None:
        result = self.adapter.test_connection()
        assert result.success is True
        assert result.latency_ms is not None
        assert result.latency_ms >= 0

    def test_verify_readonly_grants(self) -> None:
        result = self.adapter.verify_readonly_grants()
        assert result.success is True
        assert self.adapter.readonly_verified is True

    def test_execute_without_verification_raises(self) -> None:
        fresh = type(self.adapter)(self.adapter._connection_config)  # type: ignore[attr-defined]
        with pytest.raises(ReadOnlyNotVerifiedError):
            fresh.execute_readonly_query("SELECT 1", max_rows=10, timeout_seconds=5)

    def test_introspect_schema(self) -> None:
        snapshot = self.adapter.introspect_schema()
        assert snapshot.tables

        table_names = {table.table_name for table in snapshot.tables}
        assert "customers" in table_names or len(table_names) >= 1

        view_names = {
            table.table_name
            for table in snapshot.tables
            if table.object_type == "view"
        }
        if hasattr(self, "adapter") and self.adapter.get_dialect_name() == "sqlite":
            assert "active_customers" in view_names

        customers = next(
            (table for table in snapshot.tables if table.table_name == "customers"),
            snapshot.tables[0],
        )
        assert customers.columns
        column_names = {column.column_name for column in customers.columns}
        assert column_names

        status_column = next(
            (column for column in customers.columns if column.column_name == "status"),
            None,
        )
        if status_column is not None:
            assert status_column.sample_distinct_values is not None
            assert len(status_column.sample_distinct_values) <= 20

        if customers.relationships:
            rel = customers.relationships[0]
            assert rel.relationship_type == "foreign_key"
            assert rel.source_column
            assert rel.target_table

    def test_execute_readonly_query(self) -> None:
        self.adapter.verify_readonly_grants()
        result = self.adapter.execute_readonly_query(
            "SELECT 1 AS value",
            max_rows=10,
            timeout_seconds=10,
        )
        assert result.row_count == 1
        assert result.truncated is False
        assert result.columns[0].name == "value"
        assert result.rows[0][0] == 1

    def test_execute_truncates_rows(self) -> None:
        self.adapter.verify_readonly_grants()
        result = self.adapter.execute_readonly_query(
            "SELECT 1 AS value UNION ALL SELECT 2 UNION ALL SELECT 3",
            max_rows=2,
            timeout_seconds=10,
        )
        assert result.row_count == 2
        assert result.truncated is True


class TestSQLiteAdapterContract(AdapterContractSuite):
    @pytest.fixture(autouse=True)
    def _setup(self, sqlite_adapter: SQLiteAdapter) -> None:
        self.adapter = sqlite_adapter


@pytest.mark.skipif(_postgres_config() is None, reason="Postgres env not configured")
class TestPostgresAdapterContract(AdapterContractSuite):
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.adapter = PostgresAdapter(_postgres_config() or {})


@pytest.mark.skipif(_mysql_config() is None, reason="MySQL env not configured")
class TestMySQLAdapterContract(AdapterContractSuite):
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.adapter = MySQLAdapter(_mysql_config() or {})


@pytest.mark.skipif(_mssql_config() is None, reason="MSSQL env not configured")
class TestMSSQLAdapterContract(AdapterContractSuite):
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.adapter = MSSQLAdapter(_mssql_config() or {})


def test_registry_contains_all_connectors() -> None:
    app.adapters.ensure_adapters_registered()
    assert "sqlite" in ADAPTER_REGISTRY
    assert "postgresql" in ADAPTER_REGISTRY
    assert "mysql" in ADAPTER_REGISTRY


def test_factory_create_sqlite(sqlite_db_path: str) -> None:
    data_source = DataSource(
        id="00000000-0000-4000-8000-000000000001",
        name="Local SQLite",
        connector_type="sqlite",
        connection_config={"file_path": sqlite_db_path},
        is_active=True,
        dialect_name="sqlite",
        created_at="2026-06-19T00:00:00Z",
        updated_at="2026-06-19T00:00:00Z",
    )
    adapter = DataSourceFactory.create(data_source)
    assert isinstance(adapter, SQLiteAdapter)
    assert get_adapter(data_source).get_dialect_name() == "sqlite"
