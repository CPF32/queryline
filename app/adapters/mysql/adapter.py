"""MySQL adapter using PyMySQL."""

from __future__ import annotations

import re
import ssl as ssl_module
from typing import Any

try:
    import pymysql
    import pymysql.cursors
except (ImportError, OSError):  # pragma: no cover - optional driver
    pymysql = None

from app.adapters._common import (
    MAX_DISTINCT_THRESHOLD,
    MAX_SAMPLE_VALUES,
    SAMPLE_ROW_LIMIT,
    BaseDataSourceAdapter,
    ReadOnlyVerificationResult,
    attach_relationships,
    build_column_drafts,
    build_relation_draft,
)
from app.adapters.base import QueryColumnMeta, SchemaRelationshipDraft, SchemaTableDraft
from app.adapters.registry import register_adapter

WRITE_GRANT_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|TRUNCATE|GRANT|RELOAD|LOCK TABLES|"
    r"CREATE VIEW|CREATE ROUTINE|ALTER ROUTINE|EVENT|TRIGGER)\b",
    re.IGNORECASE,
)


class MySQLAdapter(BaseDataSourceAdapter):
    """MySQL / MariaDB adapter."""

    def get_dialect_name(self) -> str:
        return "mysql"

    @classmethod
    def get_connection_form_schema(cls) -> dict:
        return {
            "type": "object",
            "title": "MySQL Connection",
            "properties": {
                "host": {"type": "string", "title": "Host", "default": "localhost"},
                "port": {"type": "integer", "title": "Port", "default": 3306},
                "database": {"type": "string", "title": "Database"},
                "username": {"type": "string", "title": "Username"},
                "password": {
                    "type": "string",
                    "title": "Password",
                    "format": "password",
                },
                "ssl_mode": {
                    "type": "string",
                    "title": "SSL Mode",
                    "enum": ["disable", "require"],
                    "default": "require",
                    "description": "Use require for encrypted connections in production.",
                },
            },
            "required": ["host", "database", "username", "password"],
        }

    def _connect(self) -> "pymysql.connections.Connection":
        if pymysql is None:
            raise RuntimeError("PyMySQL is not installed.")
        config = self._connection_config
        ssl_context = None
        if config.get("ssl_mode", "require") == "require":
            ssl_context = ssl_module.create_default_context()

        conn = pymysql.connect(
            host=config.get("host", "localhost"),
            port=int(config.get("port", 3306)),
            user=config["username"],
            password=config.get("password", ""),
            database=config["database"],
            connect_timeout=30,
            read_timeout=30,
            write_timeout=30,
            cursorclass=pymysql.cursors.DictCursor,
            ssl=ssl_context,
        )
        return conn

    def _close(self, conn: pymysql.connections.Connection) -> None:
        conn.close()

    def _ping(self, conn: pymysql.connections.Connection) -> None:
        conn.ping(reconnect=False)

    def _set_statement_timeout(
        self,
        conn: pymysql.connections.Connection,
        timeout_seconds: int,
    ) -> None:
        with conn.cursor() as cur:
            cur.execute("SET SESSION MAX_EXECUTION_TIME = %s", (timeout_seconds * 1000,))

    def _check_readonly_grants(
        self,
        conn: pymysql.connections.Connection,
    ) -> ReadOnlyVerificationResult:
        with conn.cursor() as cur:
            cur.execute("SHOW GRANTS FOR CURRENT_USER()")
            grants = [next(iter(row.values())) for row in cur.fetchall()]

        for grant in grants:
            if grant.upper().startswith("GRANT ALL"):
                return ReadOnlyVerificationResult(
                    success=False,
                    message="Login has ALL PRIVILEGES.",
                )
            if WRITE_GRANT_PATTERN.search(grant):
                return ReadOnlyVerificationResult(
                    success=False,
                    message=(
                        f"Login has write or DDL privileges: {grant}. "
                        "Use a read-only user — see docs/READONLY_SETUP.md."
                    ),
                )

        return ReadOnlyVerificationResult(
            success=True,
            message="MySQL login has read-only grants.",
        )

    def _introspect_tables(
        self,
        conn: pymysql.connections.Connection,
    ) -> list[SchemaTableDraft]:
        tables: dict[str, SchemaTableDraft] = {}
        relationships: list[SchemaRelationshipDraft] = []
        database = self._connection_config["database"]

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_schema, table_name, table_rows, table_type
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_type IN ('BASE TABLE', 'VIEW')
                ORDER BY table_name
                """,
                (database,),
            )
            table_rows = cur.fetchall()

            for table_row in table_rows:
                schema_name = table_row["table_schema"]
                table_name = table_row["table_name"]
                object_type = "view" if table_row["table_type"] == "VIEW" else "table"
                qualified = self.qualify_table(schema_name, table_name)

                cur.execute(
                    """
                    SELECT column_name, column_type, is_nullable, ordinal_position
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (schema_name, table_name),
                )
                column_rows = cur.fetchall()

                pk_cols: set[str] = set()
                if object_type == "table":
                    cur.execute(
                        """
                        SELECT column_name
                        FROM information_schema.key_column_usage
                        WHERE table_schema = %s
                          AND table_name = %s
                          AND constraint_name = 'PRIMARY'
                        ORDER BY ordinal_position
                        """,
                        (schema_name, table_name),
                    )
                    pk_cols = {row["column_name"] for row in cur.fetchall()}

                columns_meta = [
                    {
                        "column_name": row["column_name"],
                        "data_type": row["column_type"],
                        "is_nullable": row["is_nullable"] == "YES",
                        "is_primary_key": row["column_name"] in pk_cols,
                        "ordinal_position": row["ordinal_position"],
                    }
                    for row in column_rows
                ]

                sample_values: dict[str, list[str] | None] = {}
                row_count: int | None = None
                if object_type == "table":
                    sample_values = self._sample_distinct_values(
                        cur, schema_name, table_name, columns_meta
                    )
                    row_count = int(table_row["table_rows"] or 0) or None

                tables[qualified] = build_relation_draft(
                    schema_name=schema_name,
                    object_name=table_name,
                    object_type=object_type,
                    columns_meta=columns_meta,
                    sample_values=sample_values,
                    row_count_estimate=row_count,
                )

            cur.execute(
                """
                SELECT
                    kcu.constraint_name,
                    kcu.table_schema AS source_schema,
                    kcu.table_name AS source_table,
                    kcu.column_name AS source_column,
                    kcu.referenced_table_schema AS target_schema,
                    kcu.referenced_table_name AS target_table,
                    kcu.referenced_column_name AS target_column
                FROM information_schema.key_column_usage kcu
                JOIN information_schema.table_constraints tc
                  ON kcu.constraint_name = tc.constraint_name
                 AND kcu.table_schema = tc.table_schema
                 AND kcu.table_name = tc.table_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND kcu.table_schema = %s
                  AND kcu.referenced_table_name IS NOT NULL
                ORDER BY kcu.constraint_name
                """,
                (database,),
            )
            for row in cur.fetchall():
                source = self.qualify_table(row["source_schema"], row["source_table"])
                target = self.qualify_table(row["target_schema"], row["target_table"])
                relationships.append(
                    SchemaRelationshipDraft(
                        constraint_name=row["constraint_name"],
                        source_table=source,
                        source_column=row["source_column"],
                        target_table=target,
                        target_column=row["target_column"],
                    )
                )

            routines = self._introspect_routines(cur, database)

        attach_relationships(tables, relationships)
        return list(tables.values()) + routines

    def _introspect_routines(
        self,
        cur: pymysql.cursors.Cursor,
        database: str,
    ) -> list[SchemaTableDraft]:
        cur.execute(
            """
            SELECT
                routine_schema,
                routine_name,
                routine_type,
                dtd_identifier,
                routine_definition,
                specific_name
            FROM information_schema.routines
            WHERE routine_schema = %s
              AND routine_type IN ('FUNCTION', 'PROCEDURE')
            ORDER BY routine_name, specific_name
            """,
            (database,),
        )
        routines: list[SchemaTableDraft] = []
        for row in cur.fetchall():
            object_type = "function" if row["routine_type"] == "FUNCTION" else "procedure"
            cur.execute(
                """
                SELECT parameter_name, dtd_identifier, ordinal_position, parameter_mode
                FROM information_schema.parameters
                WHERE specific_schema = %s
                  AND specific_name = %s
                  AND parameter_mode IN ('IN', 'INOUT', 'OUT')
                ORDER BY ordinal_position
                """,
                (row["routine_schema"], row["specific_name"]),
            )
            columns_meta = []
            for param in cur.fetchall():
                if not param["parameter_name"]:
                    continue
                columns_meta.append(
                    {
                        "column_name": param["parameter_name"],
                        "data_type": param["dtd_identifier"] or "unknown",
                        "is_nullable": True,
                        "is_primary_key": False,
                        "ordinal_position": param["ordinal_position"] or len(columns_meta) + 1,
                    }
                )
            routines.append(
                build_relation_draft(
                    schema_name=row["routine_schema"],
                    object_name=row["routine_name"],
                    object_type=object_type,
                    columns_meta=columns_meta,
                    definition=row["routine_definition"],
                    return_type=row["dtd_identifier"],
                )
            )
        return routines

    def _sample_distinct_values(
        self,
        cur: pymysql.cursors.Cursor,
        schema_name: str,
        table_name: str,
        columns_meta: list[dict[str, Any]],
    ) -> dict[str, list[str] | None]:
        qualified = f"`{schema_name}`.`{table_name}`"
        samples: dict[str, list[str] | None] = {}

        for meta in columns_meta:
            column = meta["column_name"]
            quoted_col = f"`{column}`"
            try:
                cur.execute(
                    f"""
                    SELECT COUNT(DISTINCT {quoted_col}) AS c
                    FROM (
                        SELECT {quoted_col}
                        FROM {qualified}
                        LIMIT {SAMPLE_ROW_LIMIT}
                    ) sample_rows
                    """
                )
                distinct_count = int(cur.fetchone()["c"])
                if distinct_count >= MAX_DISTINCT_THRESHOLD:
                    samples[column] = None
                    continue

                cur.execute(
                    f"""
                    SELECT DISTINCT {quoted_col} AS v
                    FROM (
                        SELECT {quoted_col}
                        FROM {qualified}
                        LIMIT {SAMPLE_ROW_LIMIT}
                    ) sample_rows
                    WHERE {quoted_col} IS NOT NULL
                    LIMIT {MAX_SAMPLE_VALUES}
                    """
                )
                values = [str(self.serialize_value(row["v"])) for row in cur.fetchall()]
                samples[column] = values or None
            except pymysql.Error:
                samples[column] = None

        return samples

    def _execute_query(
        self,
        conn: pymysql.connections.Connection,
        sql: str,
        max_rows: int,
    ) -> tuple[list[QueryColumnMeta], list[list[Any]], bool]:
        with conn.cursor() as cur:
            cur.execute(sql)
            description = cur.description or []
            columns = [
                QueryColumnMeta(name=col[0], type=str(col[1].__name__ if col[1] else "unknown"))
                for col in description
            ]
            fetched = cur.fetchmany(max_rows + 1)
            truncated = len(fetched) > max_rows
            rows = [self.serialize_row(list(row.values())) for row in fetched[:max_rows]]
            return columns, rows, truncated


register_adapter("mysql", MySQLAdapter)
