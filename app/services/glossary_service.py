"""Glossary term CRUD."""

from __future__ import annotations

import uuid

from app.db import GlossaryTermRow, db
from app.errors import NotFoundError
from app.models.glossary import GlossaryTerm
from app.repositories.mappers import glossary_term_from_row
from app.services.data_source_service import _get_row
from app.util.time import utc_now_iso


def list_terms(data_source_id: str) -> list[GlossaryTerm]:
    _get_row(data_source_id)
    rows = GlossaryTermRow.query.filter_by(data_source_id=data_source_id).order_by(
        GlossaryTermRow.term
    ).all()
    return [glossary_term_from_row(row) for row in rows]


def get_term(data_source_id: str, term_id: str) -> GlossaryTerm:
    return glossary_term_from_row(_get_term_row(data_source_id, term_id))


def create_term(
    data_source_id: str,
    *,
    term: str,
    definition: str,
    sql_expression: str | None = None,
    table_id: str | None = None,
    column_id: str | None = None,
) -> GlossaryTerm:
    _get_row(data_source_id)
    now = utc_now_iso()
    row = GlossaryTermRow(
        id=str(uuid.uuid4()),
        data_source_id=data_source_id,
        term=term,
        definition=definition,
        sql_expression=sql_expression,
        table_id=table_id,
        column_id=column_id,
        created_at=now,
        updated_at=now,
    )
    db.session.add(row)
    db.session.commit()
    return glossary_term_from_row(row)


def update_term(
    data_source_id: str,
    term_id: str,
    *,
    term: str | None = None,
    definition: str | None = None,
    sql_expression: str | None = None,
    table_id: str | None = None,
    column_id: str | None = None,
) -> GlossaryTerm:
    row = _get_term_row(data_source_id, term_id)
    if term is not None:
        row.term = term
    if definition is not None:
        row.definition = definition
    if sql_expression is not None:
        row.sql_expression = sql_expression
    if table_id is not None:
        row.table_id = table_id
    if column_id is not None:
        row.column_id = column_id
    row.updated_at = utc_now_iso()
    db.session.commit()
    return glossary_term_from_row(row)


def delete_term(data_source_id: str, term_id: str) -> None:
    row = _get_term_row(data_source_id, term_id)
    db.session.delete(row)
    db.session.commit()


def _get_term_row(data_source_id: str, term_id: str) -> GlossaryTermRow:
    row = db.session.get(GlossaryTermRow, term_id)
    if row is None or row.data_source_id != data_source_id:
        raise NotFoundError(f"Glossary term {term_id} not found.")
    return row
