"""SQL example CRUD."""

from __future__ import annotations

import uuid

from app.db import SqlExampleRow, db
from app.errors import NotFoundError
from app.models.sql_example import SqlExample
from app.repositories.mappers import sql_example_from_row
from app.services.data_source_service import _get_row
from app.util.time import utc_now_iso


def list_examples(data_source_id: str) -> list[SqlExample]:
    _get_row(data_source_id)
    rows = SqlExampleRow.query.filter_by(data_source_id=data_source_id).order_by(
        SqlExampleRow.created_at.desc()
    ).all()
    return [sql_example_from_row(row) for row in rows]


def get_example(data_source_id: str, example_id: str) -> SqlExample:
    return sql_example_from_row(_get_example_row(data_source_id, example_id))


def create_example(
    data_source_id: str,
    *,
    question: str,
    sql: str,
    notes: str | None = None,
    source: str = "manual",
) -> SqlExample:
    _get_row(data_source_id)
    now = utc_now_iso()
    row = SqlExampleRow(
        id=str(uuid.uuid4()),
        data_source_id=data_source_id,
        question=question,
        sql=sql,
        notes=notes,
        source=source,
        created_at=now,
        updated_at=now,
    )
    db.session.add(row)
    db.session.commit()
    return sql_example_from_row(row)


def update_example(
    data_source_id: str,
    example_id: str,
    *,
    question: str | None = None,
    sql: str | None = None,
    notes: str | None = None,
) -> SqlExample:
    row = _get_example_row(data_source_id, example_id)
    if question is not None:
        row.question = question
    if sql is not None:
        row.sql = sql
    if notes is not None:
        row.notes = notes
    row.updated_at = utc_now_iso()
    db.session.commit()
    return sql_example_from_row(row)


def delete_example(data_source_id: str, example_id: str) -> None:
    row = _get_example_row(data_source_id, example_id)
    db.session.delete(row)
    db.session.commit()


def _get_example_row(data_source_id: str, example_id: str) -> SqlExampleRow:
    row = db.session.get(SqlExampleRow, example_id)
    if row is None or row.data_source_id != data_source_id:
        raise NotFoundError(f"SQL example {example_id} not found.")
    return row
