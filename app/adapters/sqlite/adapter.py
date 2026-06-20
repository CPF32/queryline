"""SQLite adapter using the standard library sqlite3 module."""

from __future__ import annotations

import sqlite3
import time
from typing import Any

from app.adapters._common import (
    MAX_DISTINCT_THRESHOLD,
    MAX_SAMPLE_VALUES,
    SAMPLE_ROW_LIMIT,
    BaseDataSourceAdapter,
    ReadOnlyVerificationResult,
    attach_relationships,
    build_column_drafts,
    build_relation_draft,
    refine_column_types,
)
from app.adapters.base import QueryColumnMeta, SchemaRelationshipDraft, SchemaTableDraft
from app.adapters.registry import register_adapter


class SQLiteAdapter(BaseDataSourceAdapter):
    """Local file-based SQLite adapter for development and testing."""

    PASSWORD_FIELDS: tuple[str, ...] = ()

    def __init__(self, connection_config: dict[str, Any]) -> None:
        super().__init__(connection_config)
        file_path = connection_config.get("file_path")
        if not file_path:
            raise ValueError("SQLite connection requires 'file_path'.")
        self._file_path = str(file_path)
        self._query_deadline = 0.0

    def get_dialect_name(self) -> str:
        return "sqlite"

    @classmethod
    def get_connection_form_schema(cls) -> dict:
        return {
            "type": "object",
            "title": "SQLite Connection",
            "properties": {
                "file_path": {
                    "type": "string",
                    "title": "Database File",
                    "format": "file",
                    "description": "Absolute path to the SQLite database file on this machine.",
                }
            },
            "required": ["file_path"],
        }

    def _connect(self) -> sqlite3.Connection:
        uri = f"file:{self._file_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        return conn

    def _close(self, conn: sqlite3.Connection) -> None:
        conn.close()

    def _ping(self, conn: sqlite3.Connection) -> None:
        conn.execute("SELECT 1").fetchone()

    def _set_statement_timeout(self, conn: sqlite3.Connection, timeout_seconds: int) -> None:
        self._query_deadline = time.monotonic() + timeout_seconds

        def handler() -> int:
            if time.monotonic() > self._query_deadline:
                return 1
            return 0

        conn.set_progress_handler(handler, 1000)

    def _clear_statement_timeout(self, conn: sqlite3.Connection) -> None:
        conn.set_progress_handler(None, 0)

    def _check_readonly_grants(self, conn: sqlite3.Connection) -> ReadOnlyVerificationResult:
        try:
            conn.execute("CREATE TEMP TABLE __readonly_probe (id INTEGER)")
            return ReadOnlyVerificationResult(
                success=False,
                message=(
                    "Connection can create tables. Open SQLite in read-only mode "
                    "and ensure the file is not writable by the app user."
                ),
            )
        except sqlite3.OperationalError:
            return ReadOnlyVerificationResult(
                success=True,
                message="SQLite connection is read-only.",
            )

    def _introspect_tables(self, conn: sqlite3.Connection) -> list[SchemaTableDraft]:
        tables: dict[str, SchemaTableDraft] = {}
        relationships: list[SchemaRelationshipDraft] = []

        table_rows = conn.execute(
            """
            SELECT name, type
            FROM sqlite_master
            WHERE type IN ('table', 'view')
              AND name NOT LIKE 'sqlite_%'
            ORDER BY type, name
            """
        ).fetchall()

        for table_row in table_rows:
            table_name = table_row["name"]
            object_type = "view" if table_row["type"] == "view" else "table"
            columns_meta: list[dict[str, Any]] = []
            pk_cols: set[str] = set()

            for col in conn.execute(f"PRAGMA table_info({table_name!r})").fetchall():
                if col["pk"]:
                    pk_cols.add(col["name"])
                columns_meta.append(
                    {
                        "column_name": col["name"],
                        "data_type": col["type"] or "TEXT",
                        "is_nullable": col["notnull"] == 0,
                        "is_primary_key": col["name"] in pk_cols,
                        "ordinal_position": col["cid"] + 1,
                    }
                )

            if object_type == "table":
                for fk in conn.execute(f"PRAGMA foreign_key_list({table_name!r})").fetchall():
                    target_table = fk["table"]
                    relationships.append(
                        SchemaRelationshipDraft(
                            constraint_name=f"fk_{table_name}_{fk['from']}",
                            source_table=table_name,
                            source_column=fk["from"],
                            target_table=target_table,
                            target_column=fk["to"],
                        )
                    )

            sample_values: dict[str, list[str] | None] = {}
            row_count: int | None = None
            if object_type == "table":
                sample_values = self._sample_distinct_values(conn, None, table_name, columns_meta)
                row_count = self._estimate_row_count(conn, table_name)

            draft = build_relation_draft(
                schema_name=None,
                object_name=table_name,
                object_type=object_type,
                columns_meta=columns_meta,
                sample_values=sample_values,
                row_count_estimate=row_count,
            )
            tables[table_name] = draft

        attach_relationships(tables, relationships)
        return list(tables.values())

    def _estimate_row_count(self, conn: sqlite3.Connection, table_name: str) -> int | None:
        try:
            row = conn.execute(f"SELECT COUNT(*) AS c FROM {self._quote_ident(table_name)}").fetchone()
            return int(row["c"]) if row else None
        except sqlite3.Error:
            return None

    def _sample_distinct_values(
        self,
        conn: sqlite3.Connection,
        schema_name: str | None,
        table_name: str,
        columns_meta: list[dict[str, Any]],
    ) -> dict[str, list[str] | None]:
        del schema_name
        quoted_table = self._quote_ident(table_name)
        samples: dict[str, list[str] | None] = {}

        for meta in columns_meta:
            column = meta["column_name"]
            quoted_col = self._quote_ident(column)
            try:
                count_sql = (
                    f"SELECT COUNT(DISTINCT {quoted_col}) AS c "
                    f"FROM (SELECT {quoted_col} FROM {quoted_table} LIMIT {SAMPLE_ROW_LIMIT})"
                )
                distinct_count = int(conn.execute(count_sql).fetchone()["c"])
                if distinct_count >= MAX_DISTINCT_THRESHOLD:
                    samples[column] = None
                    continue

                value_sql = (
                    f"SELECT DISTINCT {quoted_col} AS v "
                    f"FROM (SELECT {quoted_col} FROM {quoted_table} LIMIT {SAMPLE_ROW_LIMIT}) "
                    f"WHERE {quoted_col} IS NOT NULL "
                    f"LIMIT {MAX_SAMPLE_VALUES}"
                )
                values = [
                    str(self.serialize_value(row["v"]))
                    for row in conn.execute(value_sql).fetchall()
                ]
                samples[column] = values or None
            except sqlite3.Error:
                samples[column] = None

        return samples

    def _execute_query(
        self,
        conn: sqlite3.Connection,
        sql: str,
        max_rows: int,
    ) -> tuple[list[QueryColumnMeta], list[list[Any]], bool]:
        try:
            cursor = conn.execute(sql)
            description = cursor.description or []
            columns = [
                QueryColumnMeta(name=col[0], type=col[1].__name__ if col[1] else "unknown")
                for col in description
            ]
            fetched = cursor.fetchmany(max_rows + 1)
            truncated = len(fetched) > max_rows
            rows = [self.serialize_row(tuple(row)) for row in fetched[:max_rows]]
            columns = refine_column_types(columns, rows)
            return columns, rows, truncated
        finally:
            self._clear_statement_timeout(conn)

    @staticmethod
    def _quote_ident(name: str) -> str:
        return '"' + name.replace('"', '""') + '"'


register_adapter("sqlite", SQLiteAdapter)
