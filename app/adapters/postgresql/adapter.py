"""PostgreSQL adapter using psycopg2."""

from __future__ import annotations

from typing import Any

try:
    import psycopg2
    import psycopg2.extensions
    import psycopg2.extras
except (ImportError, OSError):  # pragma: no cover - optional driver
    psycopg2 = None

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

WRITE_PRIVILEGES = frozenset(
    {"INSERT", "UPDATE", "DELETE", "TRUNCATE", "TRIGGER", "REFERENCES"}
)


class PostgresAdapter(BaseDataSourceAdapter):
    """PostgreSQL adapter."""

    def get_dialect_name(self) -> str:
        return "postgres"

    @classmethod
    def get_connection_form_schema(cls) -> dict:
        return {
            "type": "object",
            "title": "PostgreSQL Connection",
            "properties": {
                "host": {"type": "string", "title": "Host", "default": "localhost"},
                "port": {"type": "integer", "title": "Port", "default": 5432},
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
                    "enum": ["disable", "require", "verify-full"],
                    "default": "require",
                },
            },
            "required": ["host", "database", "username", "password"],
        }

    def _connect_params(self) -> dict[str, Any]:
        config = self._connection_config
        ssl_mode = config.get("ssl_mode", "require")
        sslmode_map = {
            "disable": "disable",
            "require": "require",
            "verify-full": "verify-full",
        }
        return {
            "host": config.get("host", "localhost"),
            "port": int(config.get("port", 5432)),
            "dbname": config["database"],
            "user": config["username"],
            "password": config.get("password", ""),
            "sslmode": sslmode_map.get(ssl_mode, "require"),
            "connect_timeout": 30,
        }

    def _connect(self) -> "psycopg2.extensions.connection":
        if psycopg2 is None:
            raise RuntimeError("psycopg2 is not installed.")
        conn = psycopg2.connect(**self._connect_params())
        conn.set_session(readonly=True, autocommit=True)
        return conn

    def _close(self, conn: psycopg2.extensions.connection) -> None:
        conn.close()

    def _ping(self, conn: psycopg2.extensions.connection) -> None:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")

    def _set_statement_timeout(
        self,
        conn: psycopg2.extensions.connection,
        timeout_seconds: int,
    ) -> None:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = %s", (f"{timeout_seconds}s",))

    def _check_readonly_grants(
        self,
        conn: psycopg2.extensions.connection,
    ) -> ReadOnlyVerificationResult:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT privilege_type
                FROM information_schema.role_table_grants
                WHERE grantee = current_user
                  AND privilege_type = ANY(%s)
                LIMIT 1
                """,
                (list(WRITE_PRIVILEGES),),
            )
            if cur.fetchone():
                return ReadOnlyVerificationResult(
                    success=False,
                    message=(
                        "Login has table-level write privileges (INSERT/UPDATE/DELETE/etc.). "
                        "Use a read-only role — see docs/READONLY_SETUP.md."
                    ),
                )

            cur.execute(
                "SELECT has_database_privilege(current_user, current_database(), 'CREATE')"
            )
            if cur.fetchone()[0]:
                return ReadOnlyVerificationResult(
                    success=False,
                    message="Login can CREATE objects in this database.",
                )

            cur.execute(
                """
                SELECT nspname
                FROM pg_namespace n
                WHERE has_schema_privilege(current_user, n.oid, 'CREATE')
                  AND nspname NOT LIKE 'pg_%'
                  AND nspname <> 'information_schema'
                LIMIT 1
                """
            )
            if cur.fetchone():
                return ReadOnlyVerificationResult(
                    success=False,
                    message="Login can CREATE objects in one or more schemas.",
                )

        return ReadOnlyVerificationResult(
            success=True,
            message="PostgreSQL login has read-only grants.",
        )

    def _introspect_tables(
        self,
        conn: psycopg2.extensions.connection,
    ) -> list[SchemaTableDraft]:
        tables: dict[str, SchemaTableDraft] = {}
        relationships: list[SchemaRelationshipDraft] = []

        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT table_schema, table_name, table_type
                FROM information_schema.tables
                WHERE table_type IN ('BASE TABLE', 'VIEW')
                  AND table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name
                """
            )
            table_rows = cur.fetchall()

            for table_row in table_rows:
                schema_name = table_row["table_schema"]
                table_name = table_row["table_name"]
                object_type = "view" if table_row["table_type"] == "VIEW" else "table"
                qualified = self.qualify_table(schema_name, table_name)

                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable, ordinal_position
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
                        SELECT kcu.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                          ON tc.constraint_name = kcu.constraint_name
                         AND tc.table_schema = kcu.table_schema
                        WHERE tc.constraint_type = 'PRIMARY KEY'
                          AND tc.table_schema = %s
                          AND tc.table_name = %s
                        """,
                        (schema_name, table_name),
                    )
                    pk_cols = {row["column_name"] for row in cur.fetchall()}

                columns_meta = [
                    {
                        "column_name": row["column_name"],
                        "data_type": row["data_type"],
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
                    row_count = self._estimate_row_count(cur, schema_name, table_name)

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
                    con.conname AS constraint_name,
                    src_ns.nspname AS source_schema,
                    src_rel.relname AS source_table,
                    src_att.attname AS source_column,
                    tgt_ns.nspname AS target_schema,
                    tgt_rel.relname AS target_table,
                    tgt_att.attname AS target_column
                FROM pg_constraint con
                JOIN pg_class src_rel ON src_rel.oid = con.conrelid
                JOIN pg_namespace src_ns ON src_ns.oid = src_rel.relnamespace
                JOIN pg_class tgt_rel ON tgt_rel.oid = con.confrelid
                JOIN pg_namespace tgt_ns ON tgt_ns.oid = tgt_rel.relnamespace
                JOIN unnest(con.conkey) WITH ORDINALITY AS src_keys(attnum, ord)
                  ON TRUE
                JOIN unnest(con.confkey) WITH ORDINALITY AS tgt_keys(attnum, ord)
                  ON src_keys.ord = tgt_keys.ord
                JOIN pg_attribute src_att
                  ON src_att.attrelid = src_rel.oid AND src_att.attnum = src_keys.attnum
                JOIN pg_attribute tgt_att
                  ON tgt_att.attrelid = tgt_rel.oid AND tgt_att.attnum = tgt_keys.attnum
                WHERE con.contype = 'f'
                  AND src_ns.nspname NOT IN ('pg_catalog', 'information_schema')
                ORDER BY con.conname
                """
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

            routines = self._introspect_routines(cur)

        attach_relationships(tables, relationships)
        return list(tables.values()) + routines

    def _introspect_routines(
        self,
        cur: psycopg2.extensions.cursor,
    ) -> list[SchemaTableDraft]:
        cur.execute(
            """
            SELECT
                routine_schema,
                routine_name,
                routine_type,
                data_type,
                routine_definition,
                specific_name
            FROM information_schema.routines
            WHERE routine_schema NOT IN ('pg_catalog', 'information_schema')
              AND routine_type IN ('FUNCTION', 'PROCEDURE')
            ORDER BY routine_schema, routine_name, specific_name
            """
        )
        routines: list[SchemaTableDraft] = []
        for row in cur.fetchall():
            object_type = "function" if row["routine_type"] == "FUNCTION" else "procedure"
            cur.execute(
                """
                SELECT parameter_name, data_type, ordinal_position, parameter_mode
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
                        "data_type": param["data_type"] or "unknown",
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
                    return_type=row["data_type"],
                )
            )
        return routines

    def _estimate_row_count(
        self,
        cur: psycopg2.extensions.cursor,
        schema_name: str,
        table_name: str,
    ) -> int | None:
        cur.execute(
            """
            SELECT reltuples::bigint AS estimate
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s AND c.relname = %s
            """,
            (schema_name, table_name),
        )
        row = cur.fetchone()
        if not row:
            return None
        return int(row["estimate"])

    def _sample_distinct_values(
        self,
        cur: psycopg2.extensions.cursor,
        schema_name: str,
        table_name: str,
        columns_meta: list[dict[str, Any]],
    ) -> dict[str, list[str] | None]:
        qualified = f'"{schema_name}"."{table_name}"'
        samples: dict[str, list[str] | None] = {}

        for meta in columns_meta:
            column = meta["column_name"]
            quoted_col = f'"{column}"'
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
            except psycopg2.Error:
                samples[column] = None

        return samples

    def _execute_query(
        self,
        conn: psycopg2.extensions.connection,
        sql: str,
        max_rows: int,
    ) -> tuple[list[QueryColumnMeta], list[list[Any]], bool]:
        with conn.cursor() as cur:
            cur.execute(sql)
            description = cur.description or []
            columns = [
                QueryColumnMeta(name=col.name, type=str(col.type_code))
                for col in description
            ]
            fetched = cur.fetchmany(max_rows + 1)
            truncated = len(fetched) > max_rows
            rows = [self.serialize_row(row) for row in fetched[:max_rows]]
            return columns, rows, truncated


register_adapter("postgresql", PostgresAdapter)
