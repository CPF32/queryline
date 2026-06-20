"""Query log persistence and promotion to SQL examples."""

from __future__ import annotations

import uuid
from typing import Any

from app.db import QueryLogEntryRow, db
from app.errors import NotFoundError, ValidationAppError
from app.models.query_log import QueryLogEntry
from app.models.sql_example import SqlExample
from app.repositories.mappers import query_log_from_row
from app.services.examples_service import create_example
from app.util.time import utc_now_iso


def create_query_log_entry(
    *,
    data_source_id: str,
    session_id: str,
    user_question: str,
    generated_sql: str,
    execution_status: str,
    error_message: str | None = None,
    row_count: int | None = None,
    execution_ms: float | None = None,
    chart_spec: dict[str, Any] | None = None,
    user_id: str | None = None,
    conversation_id: str | None = None,
) -> QueryLogEntry:
    row = QueryLogEntryRow(
        id=str(uuid.uuid4()),
        data_source_id=data_source_id,
        session_id=session_id,
        user_question=user_question,
        generated_sql=generated_sql,
        execution_status=execution_status,
        error_message=error_message,
        row_count=row_count,
        execution_ms=execution_ms,
        chart_spec=chart_spec,
        user_id=user_id,
        conversation_id=conversation_id,
        created_at=utc_now_iso(),
    )
    db.session.add(row)
    db.session.commit()
    return query_log_from_row(row)


def list_query_log(
    *,
    data_source_id: str | None = None,
    execution_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[QueryLogEntry], int]:
    query = QueryLogEntryRow.query
    if data_source_id:
        query = query.filter_by(data_source_id=data_source_id)
    if execution_status:
        query = query.filter_by(execution_status=execution_status)
    total = query.count()
    rows = (
        query.order_by(QueryLogEntryRow.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [query_log_from_row(row) for row in rows], total


def get_query_log_entry(entry_id: str) -> QueryLogEntry:
    row = db.session.get(QueryLogEntryRow, entry_id)
    if row is None:
        raise NotFoundError(f"Query log entry {entry_id} not found.")
    return query_log_from_row(row)


def promote_to_example(entry_id: str, *, notes: str | None = None) -> SqlExample:
    entry = get_query_log_entry(entry_id)
    if entry.execution_status != "success":
        raise ValidationAppError(
            "Only successful query log entries can be promoted to examples.",
            details={"execution_status": entry.execution_status},
        )
    return create_example(
        entry.data_source_id,
        question=entry.user_question,
        sql=entry.generated_sql,
        notes=notes,
    )
