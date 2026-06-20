"""Shared adapter utilities and base implementation."""

from __future__ import annotations

import time
from abc import abstractmethod
from typing import Any

from app.adapters.base import (
    ConnectionTestResult,
    DataSourceAdapter,
    QueryColumnMeta,
    QueryResult,
    ReadOnlyVerificationResult,
    SchemaColumnDraft,
    SchemaRelationshipDraft,
    SchemaSnapshot,
    SchemaTableDraft,
)

SAMPLE_ROW_LIMIT = 100_000
MAX_DISTINCT_THRESHOLD = 50
MAX_SAMPLE_VALUES = 20
PASSWORD_MASK = "••••••••"


class ReadOnlyNotVerifiedError(RuntimeError):
    """Raised when execute_readonly_query is called before grant verification."""


class BaseDataSourceAdapter(DataSourceAdapter):
    """Common adapter behavior: readonly gate, query truncation, value serialization."""

    PASSWORD_FIELDS: tuple[str, ...] = ("password",)

    def __init__(self, connection_config: dict[str, Any]) -> None:
        self._connection_config = dict(connection_config)
        self._readonly_verified = False

    @property
    def readonly_verified(self) -> bool:
        return self._readonly_verified

    @abstractmethod
    def _connect(self) -> Any:
        """Open and return a live connection object."""

    @abstractmethod
    def _close(self, conn: Any) -> None:
        """Close a connection opened by ``_connect``."""

    @abstractmethod
    def _ping(self, conn: Any) -> None:
        """Run a minimal query to verify the connection is alive."""

    @abstractmethod
    def _check_readonly_grants(self, conn: Any) -> ReadOnlyVerificationResult:
        """Engine-specific grant inspection."""

    @abstractmethod
    def _set_statement_timeout(self, conn: Any, timeout_seconds: int) -> None:
        """Apply a driver-level statement timeout when supported."""

    @abstractmethod
    def _introspect_tables(self, conn: Any) -> list[SchemaTableDraft]:
        """Discover tables, views, functions, procedures, columns, and relationships."""

    @abstractmethod
    def _execute_query(
        self,
        conn: Any,
        sql: str,
        max_rows: int,
    ) -> tuple[list[QueryColumnMeta], list[list[Any]], bool]:
        """Run SQL and return columns, rows, and truncated flag."""

    def test_connection(self) -> ConnectionTestResult:
        start = time.perf_counter()
        conn = None
        try:
            conn = self._connect()
            self._ping(conn)
            latency_ms = (time.perf_counter() - start) * 1000
            return ConnectionTestResult(
                success=True,
                message="Connected successfully.",
                latency_ms=round(latency_ms, 2),
            )
        except Exception as exc:
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {exc}",
                latency_ms=None,
            )
        finally:
            if conn is not None:
                self._close(conn)

    def verify_readonly_grants(self) -> ReadOnlyVerificationResult:
        conn = None
        try:
            conn = self._connect()
            result = self._check_readonly_grants(conn)
            self._readonly_verified = result.success
            return result
        except Exception as exc:
            self._readonly_verified = False
            return ReadOnlyVerificationResult(
                success=False,
                message=f"Read-only verification failed: {exc}",
            )
        finally:
            if conn is not None:
                self._close(conn)

    def introspect_schema(self) -> SchemaSnapshot:
        conn = None
        try:
            conn = self._connect()
            tables = self._introspect_tables(conn)
            return SchemaSnapshot(tables=tables)
        finally:
            if conn is not None:
                self._close(conn)

    def execute_readonly_query(
        self,
        sql: str,
        max_rows: int,
        timeout_seconds: int,
    ) -> QueryResult:
        if not self._readonly_verified:
            raise ReadOnlyNotVerifiedError(
                "Read-only grants have not been verified. "
                "Run verify_readonly_grants() when saving the connection."
            )

        start = time.perf_counter()
        conn = None
        try:
            conn = self._connect()
            self._set_statement_timeout(conn, timeout_seconds)
            columns, rows, truncated = self._execute_query(conn, sql, max_rows)
            execution_ms = round((time.perf_counter() - start) * 1000, 2)
            return QueryResult(
                columns=columns,
                rows=rows,
                row_count=len(rows),
                truncated=truncated,
                execution_ms=execution_ms,
            )
        finally:
            if conn is not None:
                self._close(conn)

    @staticmethod
    def serialize_value(value: Any) -> Any:
        """Convert a DB cell value to a JSON-serializable form."""
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (bytes, bytearray, memoryview)):
            raw = bytes(value)
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                return raw.hex()
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)

    @staticmethod
    def serialize_row(row: tuple[Any, ...] | list[Any]) -> list[Any]:
        return [BaseDataSourceAdapter.serialize_value(v) for v in row]

    @staticmethod
    def qualify_table(schema_name: str | None, table_name: str) -> str:
        if schema_name:
            return f"{schema_name}.{table_name}"
        return table_name

    @classmethod
    def password_field_names(cls) -> list[str]:
        return list(cls.PASSWORD_FIELDS)


def logical_type_from_value(value: Any) -> str:
    """Map a Python cell value to a logical result column type string."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    return "string"


def refine_column_types(
    columns: list[QueryColumnMeta],
    rows: list[list[Any]],
) -> list[QueryColumnMeta]:
    """Fill in unknown adapter type codes using sampled row values."""
    if not rows:
        return columns

    refined: list[QueryColumnMeta] = []
    for index, column in enumerate(columns):
        if column.type != "unknown":
            refined.append(column)
            continue
        sample = next(
            (row[index] for row in rows if index < len(row) and row[index] is not None),
            None,
        )
        refined.append(
            QueryColumnMeta(
                name=column.name,
                type=logical_type_from_value(sample) if sample is not None else "string",
            )
        )
    return refined


def build_column_drafts(
    columns_meta: list[dict[str, Any]],
    sample_values: dict[str, list[str] | None],
) -> list[SchemaColumnDraft]:
    drafts: list[SchemaColumnDraft] = []
    for meta in columns_meta:
        name = meta["column_name"]
        drafts.append(
            SchemaColumnDraft(
                column_name=name,
                data_type=meta["data_type"],
                is_nullable=meta["is_nullable"],
                is_primary_key=meta["is_primary_key"],
                ordinal_position=meta["ordinal_position"],
                sample_distinct_values=sample_values.get(name),
            )
        )
    return drafts


def attach_relationships(
    tables: dict[str, SchemaTableDraft],
    relationships: list[SchemaRelationshipDraft],
) -> None:
    """Attach FK relationships to their source table drafts."""
    for rel in relationships:
        source_key = rel.source_table
        if source_key in tables:
            tables[source_key].relationships.append(rel)


def build_relation_draft(
    *,
    schema_name: str | None,
    object_name: str,
    object_type: str,
    columns_meta: list[dict[str, Any]],
    sample_values: dict[str, list[str] | None] | None = None,
    row_count_estimate: int | None = None,
    definition: str | None = None,
    return_type: str | None = None,
) -> SchemaTableDraft:
    """Build a schema object draft for tables, views, or routines."""
    return SchemaTableDraft(
        schema_name=schema_name,
        table_name=object_name,
        object_type=object_type,
        row_count_estimate=row_count_estimate,
        definition=definition,
        return_type=return_type,
        columns=build_column_drafts(columns_meta, sample_values or {}),
        relationships=[],
    )
