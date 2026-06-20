"""Microsoft SQL Server adapter using pyodbc."""

from __future__ import annotations

from typing import Any

try:
    import pyodbc
except (ImportError, OSError):  # pragma: no cover - environment-specific
    pyodbc = None

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


class MSSQLAdapter(BaseDataSourceAdapter):
    """SQL Server adapter."""

    def get_dialect_name(self) -> str:
        return "tsql"

    @classmethod
    def get_connection_form_schema(cls) -> dict:
        return {
            "type": "object",
            "title": "SQL Server Connection",
            "properties": {
                "host": {"type": "string", "title": "Host"},
                "port": {"type": "integer", "title": "Port", "default": 1433},
                "database": {"type": "string", "title": "Database"},
                "auth_mode": {
                    "type": "string",
                    "title": "Authentication",
                    "enum": ["sql", "windows"],
                    "default": "sql",
                },
                "username": {"type": "string", "title": "Username"},
                "password": {
                    "type": "string",
                    "title": "Password",
                    "format": "password",
                },
                "driver": {
                    "type": "string",
                    "title": "ODBC Driver",
                    "default": "ODBC Driver 18 for SQL Server",
                    "description": "Installed ODBC driver name.",
                },
                "encrypt": {
                    "type": "string",
                    "title": "Encrypt",
                    "enum": ["yes", "no"],
                    "default": "yes",
                },
                "trust_server_certificate": {
                    "type": "string",
                    "title": "Trust Server Certificate",
                    "enum": ["yes", "no"],
                    "default": "no",
                },
            },
            "required": ["host", "database", "auth_mode"],
        }

    def _build_connection_string(self) -> str:
        config = self._connection_config
        driver = config.get("driver", "ODBC Driver 18 for SQL Server")
        host = config["host"]
        port = int(config.get("port", 1433))
        database = config["database"]
        auth_mode = config.get("auth_mode", "sql")
        encrypt = config.get("encrypt", "yes")
        trust = config.get("trust_server_certificate", "no")

        parts = [
            f"DRIVER={{{driver}}}",
            f"SERVER={host},{port}",
            f"DATABASE={database}",
            f"Encrypt={encrypt}",
            f"TrustServerCertificate={trust}",
        ]

        if auth_mode == "windows":
            parts.append("Trusted_Connection=yes")
        else:
            parts.append(f"UID={config.get('username', '')}")
            parts.append(f"PWD={config.get('password', '')}")

        return ";".join(parts)

    def _connect(self) -> "pyodbc.Connection":
        if pyodbc is None:
            raise RuntimeError(
                "pyodbc is not available. Install unixODBC and the SQL Server ODBC driver."
            )
        conn = pyodbc.connect(self._build_connection_string(), timeout=30, autocommit=True)
        return conn

    def _close(self, conn: pyodbc.Connection) -> None:
        conn.close()

    def _ping(self, conn: pyodbc.Connection) -> None:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        finally:
            cursor.close()

    def _set_statement_timeout(self, conn: pyodbc.Connection, timeout_seconds: int) -> None:
        conn.timeout = timeout_seconds

    def _check_readonly_grants(self, conn: pyodbc.Connection) -> ReadOnlyVerificationResult:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT DISTINCT permission_name
                FROM fn_my_permissions(NULL, 'DATABASE')
                WHERE permission_name IN (
                    'INSERT', 'UPDATE', 'DELETE', 'ALTER', 'CONTROL',
                    'CREATE TABLE', 'CREATE VIEW', 'CREATE PROCEDURE'
                )
                """
            )
            db_perms = {row[0] for row in cursor.fetchall()}
            if db_perms:
                return ReadOnlyVerificationResult(
                    success=False,
                    message=f"Login has database-level write/DDL permissions: {sorted(db_perms)}.",
                )

            cursor.execute(
                """
                SELECT DISTINCT
                    SCHEMA_NAME(o.schema_id) AS schema_name,
                    o.name AS object_name,
                    p.permission_name
                FROM sys.database_permissions p
                JOIN sys.objects o ON p.major_id = o.object_id
                JOIN sys.database_principals dp ON p.grantee_principal_id = dp.principal_id
                WHERE dp.name = USER_NAME()
                  AND p.permission_name IN (
                      'INSERT', 'UPDATE', 'DELETE', 'ALTER', 'CONTROL',
                      'TAKE OWNERSHIP', 'REFERENCES', 'TRIGGER'
                  )
                """
            )
            row = cursor.fetchone()
            if row:
                return ReadOnlyVerificationResult(
                    success=False,
                    message=(
                        f"Login has object-level permission {row.permission_name} "
                        f"on {row.schema_name}.{row.object_name}."
                    ),
                )

            cursor.execute("SELECT IS_MEMBER('db_owner')")
            if cursor.fetchone()[0]:
                return ReadOnlyVerificationResult(
                    success=False,
                    message="Login is a member of db_owner.",
                )

            cursor.execute("SELECT IS_SRVROLEMEMBER('sysadmin')")
            if cursor.fetchone()[0]:
                return ReadOnlyVerificationResult(
                    success=False,
                    message="Login is a member of sysadmin.",
                )
        finally:
            cursor.close()

        return ReadOnlyVerificationResult(
            success=True,
            message="SQL Server login has read-only grants.",
        )

    def _introspect_tables(self, conn: pyodbc.Connection) -> list[SchemaTableDraft]:
        tables: dict[str, SchemaTableDraft] = {}
        relationships: list[SchemaRelationshipDraft] = []
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW')
                ORDER BY TABLE_SCHEMA, TABLE_NAME
                """
            )
            table_rows = cursor.fetchall()

            for schema_name, table_name, table_type in table_rows:
                object_type = "view" if table_type == "VIEW" else "table"
                qualified = self.qualify_table(schema_name, table_name)

                cursor.execute(
                    """
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, ORDINAL_POSITION
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
                    ORDER BY ORDINAL_POSITION
                    """,
                    (schema_name, table_name),
                )
                column_rows = cursor.fetchall()

                pk_cols: set[str] = set()
                if object_type == "table":
                    cursor.execute(
                        """
                        SELECT kcu.COLUMN_NAME
                        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                          ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                         AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
                        WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                          AND tc.TABLE_SCHEMA = ?
                          AND tc.TABLE_NAME = ?
                        """,
                        (schema_name, table_name),
                    )
                    pk_cols = {row[0] for row in cursor.fetchall()}

                columns_meta = [
                    {
                        "column_name": row[0],
                        "data_type": row[1],
                        "is_nullable": row[2] == "YES",
                        "is_primary_key": row[0] in pk_cols,
                        "ordinal_position": row[3],
                    }
                    for row in column_rows
                ]

                sample_values: dict[str, list[str] | None] = {}
                row_count: int | None = None
                if object_type == "table":
                    sample_values = self._sample_distinct_values(
                        cursor, schema_name, table_name, columns_meta
                    )
                    row_count = self._estimate_row_count(cursor, schema_name, table_name)

                tables[qualified] = build_relation_draft(
                    schema_name=schema_name,
                    object_name=table_name,
                    object_type=object_type,
                    columns_meta=columns_meta,
                    sample_values=sample_values,
                    row_count_estimate=row_count,
                )

            cursor.execute(
                """
                SELECT
                    fk.name AS constraint_name,
                    sch_src.name AS source_schema,
                    tab_src.name AS source_table,
                    col_src.name AS source_column,
                    sch_tgt.name AS target_schema,
                    tab_tgt.name AS target_table,
                    col_tgt.name AS target_column
                FROM sys.foreign_keys fk
                JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
                JOIN sys.tables tab_src ON fkc.parent_object_id = tab_src.object_id
                JOIN sys.schemas sch_src ON tab_src.schema_id = sch_src.schema_id
                JOIN sys.columns col_src
                  ON fkc.parent_object_id = col_src.object_id
                 AND fkc.parent_column_id = col_src.column_id
                JOIN sys.tables tab_tgt ON fkc.referenced_object_id = tab_tgt.object_id
                JOIN sys.schemas sch_tgt ON tab_tgt.schema_id = sch_tgt.schema_id
                JOIN sys.columns col_tgt
                  ON fkc.referenced_object_id = col_tgt.object_id
                 AND fkc.referenced_column_id = col_tgt.column_id
                ORDER BY fk.name
                """
            )
            for row in cursor.fetchall():
                source = self.qualify_table(row.source_schema, row.source_table)
                target = self.qualify_table(row.target_schema, row.target_table)
                relationships.append(
                    SchemaRelationshipDraft(
                        constraint_name=row.constraint_name,
                        source_table=source,
                        source_column=row.source_column,
                        target_table=target,
                        target_column=row.target_column,
                    )
                )

            routines = self._introspect_routines(cursor)
        finally:
            cursor.close()

        attach_relationships(tables, relationships)
        return list(tables.values()) + routines

    def _introspect_routines(self, cursor: pyodbc.Cursor) -> list[SchemaTableDraft]:
        cursor.execute(
            """
            SELECT
                ROUTINE_SCHEMA,
                ROUTINE_NAME,
                ROUTINE_TYPE,
                DATA_TYPE,
                ROUTINE_DEFINITION,
                SPECIFIC_NAME
            FROM INFORMATION_SCHEMA.ROUTINES
            WHERE ROUTINE_TYPE IN ('FUNCTION', 'PROCEDURE')
            ORDER BY ROUTINE_SCHEMA, ROUTINE_NAME, SPECIFIC_NAME
            """
        )
        routines: list[SchemaTableDraft] = []
        for row in cursor.fetchall():
            object_type = "function" if row.ROUTINE_TYPE == "FUNCTION" else "procedure"
            cursor.execute(
                """
                SELECT PARAMETER_NAME, DATA_TYPE, ORDINAL_POSITION, PARAMETER_MODE
                FROM INFORMATION_SCHEMA.PARAMETERS
                WHERE SPECIFIC_SCHEMA = ? AND SPECIFIC_NAME = ?
                  AND PARAMETER_MODE IN ('IN', 'INOUT', 'OUT')
                ORDER BY ORDINAL_POSITION
                """,
                (row.ROUTINE_SCHEMA, row.SPECIFIC_NAME),
            )
            columns_meta = []
            for param in cursor.fetchall():
                if not param.PARAMETER_NAME:
                    continue
                columns_meta.append(
                    {
                        "column_name": param.PARAMETER_NAME,
                        "data_type": param.DATA_TYPE or "unknown",
                        "is_nullable": True,
                        "is_primary_key": False,
                        "ordinal_position": param.ORDINAL_POSITION or len(columns_meta) + 1,
                    }
                )
            routines.append(
                build_relation_draft(
                    schema_name=row.ROUTINE_SCHEMA,
                    object_name=row.ROUTINE_NAME,
                    object_type=object_type,
                    columns_meta=columns_meta,
                    definition=row.ROUTINE_DEFINITION,
                    return_type=row.DATA_TYPE,
                )
            )
        return routines

    def _estimate_row_count(
        self,
        cursor: pyodbc.Cursor,
        schema_name: str,
        table_name: str,
    ) -> int | None:
        cursor.execute(
            """
            SELECT SUM(p.rows) AS row_count
            FROM sys.partitions p
            JOIN sys.tables t ON p.object_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name = ? AND t.name = ? AND p.index_id IN (0, 1)
            GROUP BY t.object_id
            """,
            (schema_name, table_name),
        )
        row = cursor.fetchone()
        if not row or row.row_count is None:
            return None
        return int(row.row_count)

    def _sample_distinct_values(
        self,
        cursor: pyodbc.Cursor,
        schema_name: str,
        table_name: str,
        columns_meta: list[dict[str, Any]],
    ) -> dict[str, list[str] | None]:
        qualified = f"[{schema_name}].[{table_name}]"
        samples: dict[str, list[str] | None] = {}

        for meta in columns_meta:
            column = meta["column_name"]
            quoted_col = f"[{column}]"
            try:
                cursor.execute(
                    f"""
                    SELECT COUNT(DISTINCT {quoted_col}) AS c
                    FROM (
                        SELECT TOP ({SAMPLE_ROW_LIMIT}) {quoted_col}
                        FROM {qualified}
                    ) sample_rows
                    """
                )
                distinct_count = int(cursor.fetchone().c)
                if distinct_count >= MAX_DISTINCT_THRESHOLD:
                    samples[column] = None
                    continue

                cursor.execute(
                    f"""
                    SELECT DISTINCT TOP ({MAX_SAMPLE_VALUES}) {quoted_col} AS v
                    FROM (
                        SELECT TOP ({SAMPLE_ROW_LIMIT}) {quoted_col}
                        FROM {qualified}
                    ) sample_rows
                    WHERE {quoted_col} IS NOT NULL
                    """
                )
                values = [str(self.serialize_value(row.v)) for row in cursor.fetchall()]
                samples[column] = values or None
            except pyodbc.Error:
                samples[column] = None

        return samples

    def _execute_query(
        self,
        conn: pyodbc.Connection,
        sql: str,
        max_rows: int,
    ) -> tuple[list[QueryColumnMeta], list[list[Any]], bool]:
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            description = cursor.description or []
            columns = [
                QueryColumnMeta(
                    name=col[0],
                    type=str(col[1].__name__ if hasattr(col[1], "__name__") else col[1]),
                )
                for col in description
            ]
            fetched = cursor.fetchmany(max_rows + 1)
            truncated = len(fetched) > max_rows
            rows = [self.serialize_row(tuple(row)) for row in fetched[:max_rows]]
            return columns, rows, truncated
        finally:
            cursor.close()


register_adapter("mssql", MSSQLAdapter)
