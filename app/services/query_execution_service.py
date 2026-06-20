"""SQL validation and read-only execution orchestration.

Validates SELECT-only single statements via sqlglot, then delegates execution
to the active DataSourceAdapter. Creates QueryLogEntry records.

See CONTRACTS.md §5.9 and §6.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Any

import sqlglot
from sqlglot import exp, parse_one
from sqlglot.errors import ParseError

from app.adapters._common import BaseDataSourceAdapter
from app.adapters.base import QueryResult
from app.errors import ValidationAppError
from app.repositories.mappers import data_source_from_row
from app.services.adapter_factory import DataSourceFactory
from app.services.data_source_service import _get_row as get_data_source_row
from app.services.query_log_service import create_query_log_entry
from app.services.schema_service import list_columns, list_tables
from app.services.sql_generation_service import MAX_GENERATION_ATTEMPTS, generate_sql

DEFAULT_ROW_LIMIT = 1000
DEFAULT_TIMEOUT_SECONDS = 30

READONLY_ROOT_TYPES = (exp.Select, exp.Union, exp.Intersect, exp.Except, exp.Subquery)

FORBIDDEN_EXPRESSION_TYPES: tuple[type[exp.Expression], ...] = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.TruncateTable,
    exp.Merge,
    exp.Execute,
    exp.Command,
    exp.Transaction,
    exp.Commit,
    exp.Rollback,
    exp.Grant,
    exp.Revoke,
    exp.Copy,
    exp.Into,
)

FORBIDDEN_LABELS: dict[type[exp.Expression], str] = {
    exp.Insert: "INSERT",
    exp.Update: "UPDATE",
    exp.Delete: "DELETE",
    exp.Drop: "DROP",
    exp.Create: "CREATE",
    exp.Alter: "ALTER",
    exp.TruncateTable: "TRUNCATE",
    exp.Merge: "MERGE",
    exp.Execute: "EXEC",
    exp.Command: "COMMAND",
    exp.Into: "SELECT INTO",
}


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of static SQL validation before execution."""

    valid: bool
    sql: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    error_category: str | None = None


class QueryExecutionError(Exception):
    """Normalized execution failure for retry loops and API responses."""

    def __init__(
        self,
        message: str,
        *,
        category: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.category = category
        self.details = details or {}


@dataclass(frozen=True)
class ExecuteQueryOutcome:
    success: bool
    query_log_id: str
    validated_sql: str | None = None
    query_result: QueryResult | None = None
    validation_result: ValidationResult | None = None
    execution_error: QueryExecutionError | None = None


@dataclass(frozen=True)
class GenerateAndExecuteOutcome:
    success: bool
    attempts: int
    sql: str | None = None
    explanation: str | None = None
    query_result: QueryResult | None = None
    query_log_id: str | None = None
    confidence: str | None = None
    tables_used: list[str] | None = None
    error_message: str | None = None
    error_category: str | None = None


def _normalize_identifier(name: str) -> str:
    cleaned = name.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    cleaned = cleaned.strip('"').strip("`")
    return cleaned.lower()


def _normalize_table_key(name: str) -> str:
    return _normalize_identifier(name)


def build_schema_catalog(data_source_id: str) -> tuple[set[str], dict[str, set[str]]]:
    """Build known table/column sets from persisted schema metadata."""
    get_data_source_row(data_source_id)
    known_tables: set[str] = set()
    known_columns: dict[str, set[str]] = {}

    for table in list_tables(data_source_id):
        if getattr(table, "object_type", "table") not in {"table", "view"}:
            continue
        qualified = BaseDataSourceAdapter.qualify_table(table.schema_name, table.table_name)
        keys = {
            _normalize_table_key(qualified),
            _normalize_table_key(table.table_name),
        }
        columns = {
            _normalize_identifier(column.column_name)
            for column in list_columns(data_source_id, table.id)
        }
        for key in keys:
            known_tables.add(key)
            known_columns[key] = columns

    return known_tables, known_columns


def _invalid(
    *,
    code: str,
    message: str,
    category: str,
) -> ValidationResult:
    return ValidationResult(
        valid=False,
        error_code=code,
        error_message=message,
        error_category=category,
    )


def _resolve_table_reference(
    schema: str | None,
    table: str,
    known_tables: set[str],
) -> str | None:
    if not table:
        return None

    candidates = []
    if schema:
        candidates.append(_normalize_table_key(f"{schema}.{table}"))
    candidates.append(_normalize_table_key(table))

    for candidate in candidates:
        if candidate in known_tables:
            return candidate

    bare = _normalize_table_key(table)
    matches = [known for known in known_tables if known == bare or known.endswith(f".{bare}")]
    if len(matches) == 1:
        return matches[0]
    return None


def _build_alias_map(expression: exp.Expression) -> dict[str, str]:
    alias_map: dict[str, str] = {}
    for table in expression.find_all(exp.Table):
        real_name = _normalize_table_key(
            BaseDataSourceAdapter.qualify_table(table.db, table.name)
            if table.db
            else table.name
        )
        alias_map[_normalize_identifier(table.name)] = real_name
        alias_or_name = table.alias_or_name
        if alias_or_name:
            alias_map[_normalize_identifier(alias_or_name)] = real_name
    return alias_map


def _resolve_column_table(
    column: exp.Column,
    alias_map: dict[str, str],
) -> str | None:
    if not column.table:
        return None
    table_ref = _normalize_identifier(column.table)
    return alias_map.get(table_ref, table_ref)


def _suggest_column(name: str, candidates: set[str]) -> str | None:
    matches = difflib.get_close_matches(name, sorted(candidates), n=1, cutoff=0.6)
    return matches[0] if matches else None


def _select_from_clause(expression: exp.Select) -> exp.Expression | None:
    return expression.args.get("from_") or expression.args.get("from")


def _has_row_limit(expression: exp.Expression) -> bool:
    if expression.args.get("limit") is not None:
        return True
    if isinstance(expression, exp.Subquery):
        return _has_row_limit(expression.this)
    if isinstance(expression, (exp.Union, exp.Intersect, exp.Except)):
        return expression.args.get("limit") is not None
    return False


def _contains_aggregate(expression: exp.Expression) -> bool:
    return expression.find(exp.AggFunc) is not None


def _returns_at_most_one_row(expression: exp.Expression) -> bool:
    if _has_row_limit(expression):
        return True

    if isinstance(expression, exp.Subquery):
        return _returns_at_most_one_row(expression.this)

    if isinstance(expression, (exp.Union, exp.Intersect, exp.Except)):
        return False

    if isinstance(expression, exp.Select):
        if expression.args.get("group"):
            return False
        if not _select_from_clause(expression):
            return True
        if expression.expressions and all(_contains_aggregate(expr) for expr in expression.expressions):
            return True

    return False


def _inject_row_limit(expression: exp.Expression, dialect: str, max_rows: int) -> exp.Expression:
    limited = expression.limit(max_rows, copy=True, dialect=dialect)
    return limited


def _single_table_context(
    expression: exp.Expression,
    known_tables: set[str],
) -> str | None:
    resolved_tables: set[str] = set()
    for table in expression.find_all(exp.Table):
        resolved = _resolve_table_reference(table.db, table.name, known_tables)
        if resolved is not None:
            resolved_tables.add(resolved)
    if len(resolved_tables) == 1:
        return next(iter(resolved_tables))
    return None


def _validate_tables_and_columns(
    expression: exp.Expression,
    known_tables: set[str],
    known_columns: dict[str, set[str]],
) -> ValidationResult | None:
    alias_map = _build_alias_map(expression)
    single_table = _single_table_context(expression, known_tables)

    for table in expression.find_all(exp.Table):
        resolved = _resolve_table_reference(table.db, table.name, known_tables)
        if resolved is None:
            display = (
                BaseDataSourceAdapter.qualify_table(table.db, table.name)
                if table.db
                else table.name
            )
            available = sorted(known_tables)
            hint = ""
            suggestion = _suggest_column(_normalize_table_key(display), set(known_tables))
            if suggestion and suggestion != _normalize_table_key(display):
                hint = f" — did you mean '{suggestion}'?"
            return _invalid(
                code="unknown_table",
                message=f"Table '{display}' is not in the schema metadata{hint}.",
                category="table_not_found",
            )

    for column in expression.find_all(exp.Column):
        if not column.name or column.name == "*":
            continue
        resolved_table = _resolve_column_table(column, alias_map)
        if resolved_table is None and single_table is not None:
            resolved_table = single_table
        if resolved_table is None:
            continue

        table_key = _resolve_table_reference(None, resolved_table, known_tables) or resolved_table
        if table_key not in known_columns:
            continue

        column_name = _normalize_identifier(column.name)
        allowed = known_columns[table_key]
        if column_name in allowed:
            continue

        suggestion = _suggest_column(column_name, allowed)
        hint = f" — did you mean '{suggestion}'?" if suggestion else ""
        return _invalid(
            code="unknown_column",
            message=(
                f"Column '{column.name}' not found on table '{table_key}'{hint}"
            ),
            category="column_not_found",
        )

    return None


def validate_sql(
    sql: str,
    dialect: str,
    known_tables: set[str],
    known_columns: dict[str, set[str]],
    *,
    max_rows: int = DEFAULT_ROW_LIMIT,
) -> ValidationResult:
    """Validate SQL is a safe, schema-aligned read-only SELECT."""
    stripped = sql.strip()
    if not stripped:
        return _invalid(
            code="empty_sql",
            message="SQL must not be empty.",
            category="syntax_error",
        )

    try:
        expression = parse_one(stripped, read=dialect)
    except ParseError as exc:
        return _invalid(
            code="parse_error",
            message=f"SQL parse error: {exc}",
            category="syntax_error",
        )

    if isinstance(expression, exp.Block):
        return _invalid(
            code="multiple_statements",
            message="Multiple SQL statements are not allowed — submit exactly one SELECT.",
            category="forbidden_statement",
        )

    if len(sqlglot.parse(stripped, read=dialect)) > 1:
        return _invalid(
            code="multiple_statements",
            message="Multiple SQL statements are not allowed — submit exactly one SELECT.",
            category="forbidden_statement",
        )

    if isinstance(expression, exp.Drop):
        return _invalid(
            code="forbidden_statement",
            message="DROP statements are not allowed — only read-only SELECT queries are permitted.",
            category="forbidden_statement",
        )

    if not isinstance(expression, READONLY_ROOT_TYPES):
        return _invalid(
            code="not_select",
            message=(
                f"Only a single read-only SELECT query is allowed; "
                f"got {type(expression).__name__}."
            ),
            category="forbidden_statement",
        )

    for node in expression.find_all(FORBIDDEN_EXPRESSION_TYPES):
        label = FORBIDDEN_LABELS.get(type(node), type(node).__name__.upper())
        return _invalid(
            code="forbidden_statement",
            message=(
                f"{label} statements are not allowed — only read-only SELECT queries "
                "are permitted."
            ),
            category="forbidden_statement",
        )

    schema_error = _validate_tables_and_columns(expression, known_tables, known_columns)
    if schema_error is not None:
        return schema_error

    final_expression = expression
    if not _returns_at_most_one_row(expression):
        final_expression = _inject_row_limit(expression, dialect, max_rows)

    validated_sql = final_expression.sql(dialect=dialect)
    return ValidationResult(valid=True, sql=validated_sql)


def classify_execution_error(exc: Exception) -> tuple[str, str]:
    """Map adapter/driver exceptions to retry-friendly categories."""
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()

    if isinstance(exc, TimeoutError) or re.search(r"timeout|timed out|time exceeded|query timeout", lowered):
        return "timeout", message

    if re.search(
        r"no such column|unknown column|invalid column name|undefined column|column .* does not exist",
        lowered,
    ):
        return "column_not_found", message

    if re.search(
        r"no such table|unknown table|invalid object name|relation .* does not exist|"
        r"table .* doesn't exist|table .* does not exist",
        lowered,
    ):
        return "table_not_found", message

    if re.search(r"syntax error|near \"|near '|sql syntax|malformed", lowered):
        return "syntax_error", message

    return "unknown", message


def execute_validated_query(
    sql: str,
    data_source_id: str,
    max_rows: int,
    timeout_seconds: int,
) -> QueryResult:
    """Execute SQL that has already passed validation."""
    row = get_data_source_row(data_source_id)
    adapter = DataSourceFactory.get_adapter(data_source_from_row(row))
    if not adapter.readonly_verified:
        verification = adapter.verify_readonly_grants()
        if not verification.success:
            raise QueryExecutionError(
                verification.message,
                category="validation_error",
            )
    try:
        return adapter.execute_readonly_query(
            sql,
            max_rows=max_rows,
            timeout_seconds=timeout_seconds,
        )
    except Exception as exc:
        category, message = classify_execution_error(exc)
        raise QueryExecutionError(message, category=category, details={"exception": exc.__class__.__name__}) from exc


def execute_with_validation(
    *,
    data_source_id: str,
    session_id: str,
    sql: str,
    user_question: str,
    max_rows: int = DEFAULT_ROW_LIMIT,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    user_id: str | None = None,
    conversation_id: str | None = None,
) -> ExecuteQueryOutcome:
    """Validate SQL, execute when valid, and persist a query log entry."""
    row = get_data_source_row(data_source_id)
    known_tables, known_columns = build_schema_catalog(data_source_id)
    validation = validate_sql(
        sql,
        row.dialect_name,
        known_tables,
        known_columns,
        max_rows=max_rows,
    )

    if not validation.valid:
        log_entry = create_query_log_entry(
            data_source_id=data_source_id,
            session_id=session_id,
            user_question=user_question,
            generated_sql=sql,
            execution_status="validation_error",
            error_message=validation.error_message,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        return ExecuteQueryOutcome(
            success=False,
            query_log_id=log_entry.id,
            validation_result=validation,
        )

    assert validation.sql is not None
    try:
        query_result = execute_validated_query(
            validation.sql,
            data_source_id,
            max_rows=max_rows,
            timeout_seconds=timeout_seconds,
        )
    except QueryExecutionError as exc:
        log_entry = create_query_log_entry(
            data_source_id=data_source_id,
            session_id=session_id,
            user_question=user_question,
            generated_sql=validation.sql,
            execution_status="execution_error",
            error_message=exc.message,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        return ExecuteQueryOutcome(
            success=False,
            query_log_id=log_entry.id,
            validated_sql=validation.sql,
            validation_result=validation,
            execution_error=exc,
        )

    log_entry = create_query_log_entry(
        data_source_id=data_source_id,
        session_id=session_id,
        user_question=user_question,
        generated_sql=validation.sql,
        execution_status="success",
        row_count=query_result.row_count,
        execution_ms=query_result.execution_ms,
        user_id=user_id,
        conversation_id=conversation_id,
    )
    return ExecuteQueryOutcome(
        success=True,
        query_log_id=log_entry.id,
        validated_sql=validation.sql,
        query_result=query_result,
        validation_result=validation,
    )


def execute_query(
    *,
    data_source_id: str,
    session_id: str,
    sql: str,
    user_question: str,
    max_rows: int = DEFAULT_ROW_LIMIT,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    user_id: str | None = None,
    conversation_id: str | None = None,
) -> tuple[QueryResult, str]:
    """Validate and execute SQL; raise ValidationAppError when blocked."""
    outcome = execute_with_validation(
        data_source_id=data_source_id,
        session_id=session_id,
        sql=sql,
        user_question=user_question,
        max_rows=max_rows,
        timeout_seconds=timeout_seconds,
        user_id=user_id,
        conversation_id=conversation_id,
    )
    if outcome.success:
        assert outcome.query_result is not None
        return outcome.query_result, outcome.query_log_id

    if outcome.validation_result and not outcome.validation_result.valid:
        raise ValidationAppError(
            outcome.validation_result.error_message or "SQL validation failed.",
            details={
                "query_log_id": outcome.query_log_id,
                "error_code": outcome.validation_result.error_code,
                "error_category": outcome.validation_result.error_category,
            },
        )
    if outcome.execution_error:
        raise ValidationAppError(
            outcome.execution_error.message,
            details={
                "query_log_id": outcome.query_log_id,
                "error_category": outcome.execution_error.category,
                **outcome.execution_error.details,
            },
        )
    raise ValidationAppError(
        "Query execution failed.",
        details={"query_log_id": outcome.query_log_id},
    )


def generate_and_execute(
    *,
    data_source_id: str,
    session_id: str,
    question: str,
    conversation_history: list[dict[str, str]] | None = None,
    max_rows: int = DEFAULT_ROW_LIMIT,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    claude_client: Any | None = None,
) -> GenerateAndExecuteOutcome:
    """Generate SQL, validate, execute, and retry generation on failure."""
    row = get_data_source_row(data_source_id)
    known_tables, known_columns = build_schema_catalog(data_source_id)
    retry_context: dict[str, Any] | None = None
    last_log_id: str | None = None
    last_sql: str | None = None
    last_error: str | None = None
    last_category: str | None = None

    for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
        attempt_context = {"attempt_number": attempt, **(retry_context or {})}
        generation = generate_sql(
            question,
            data_source_id,
            conversation_history=conversation_history,
            retry_context=attempt_context,
            claude_client=claude_client,
        )

        if not generation.success or not generation.sql:
            last_error = generation.error_message or generation.explanation
            last_category = "generation_error"
            log_entry = create_query_log_entry(
                data_source_id=data_source_id,
                session_id=session_id,
                user_question=question,
                generated_sql=generation.sql or "",
                execution_status="execution_error",
                error_message=last_error,
            )
            last_log_id = log_entry.id
            retry_context = {
                "previous_sql": generation.sql or "",
                "execution_error": last_error or "SQL generation failed.",
            }
            continue

        last_sql = generation.sql
        validation = validate_sql(
            generation.sql,
            row.dialect_name,
            known_tables,
            known_columns,
            max_rows=max_rows,
        )

        if not validation.valid:
            last_error = validation.error_message
            last_category = validation.error_category
            log_entry = create_query_log_entry(
                data_source_id=data_source_id,
                session_id=session_id,
                user_question=question,
                generated_sql=generation.sql,
                execution_status="validation_error",
                error_message=validation.error_message,
            )
            last_log_id = log_entry.id
            retry_context = {
                "previous_sql": generation.sql,
                "execution_error": validation.error_message or "Validation failed.",
            }
            continue

        assert validation.sql is not None
        try:
            query_result = execute_validated_query(
                validation.sql,
                data_source_id,
                max_rows=max_rows,
                timeout_seconds=timeout_seconds,
            )
        except QueryExecutionError as exc:
            last_error = exc.message
            last_category = exc.category
            log_entry = create_query_log_entry(
                data_source_id=data_source_id,
                session_id=session_id,
                user_question=question,
                generated_sql=validation.sql,
                execution_status="execution_error",
                error_message=exc.message,
            )
            last_log_id = log_entry.id
            retry_context = {
                "previous_sql": validation.sql,
                "execution_error": exc.message,
            }
            continue

        log_entry = create_query_log_entry(
            data_source_id=data_source_id,
            session_id=session_id,
            user_question=question,
            generated_sql=validation.sql,
            execution_status="success",
            row_count=query_result.row_count,
            execution_ms=query_result.execution_ms,
        )
        return GenerateAndExecuteOutcome(
            success=True,
            attempts=attempt,
            sql=validation.sql,
            explanation=generation.explanation,
            query_result=query_result,
            query_log_id=log_entry.id,
            confidence=generation.confidence,
            tables_used=generation.tables_used,
        )

    return GenerateAndExecuteOutcome(
        success=False,
        attempts=MAX_GENERATION_ATTEMPTS,
        sql=last_sql,
        query_log_id=last_log_id,
        error_message=last_error or "Query could not be executed.",
        error_category=last_category,
    )
