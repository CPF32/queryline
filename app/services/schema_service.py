"""Schema metadata CRUD and live import orchestration.

Coordinates adapter introspection with persisted SchemaTable, SchemaColumn,
and SchemaRelationship records. Does not execute user queries.

See CONTRACTS.md §5.4–§5.5 and §6.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.adapters._common import BaseDataSourceAdapter
from app.adapters.base import SCHEMA_OBJECT_TYPES, SchemaSnapshot, SchemaTableDraft
from app.db import (
    SchemaColumnRow,
    SchemaRelationshipRow,
    SchemaTableRow,
    db,
)
from app.errors import NotFoundError, ValidationAppError
from app.models.data_source import DataSource
from app.models.schema import SchemaColumn, SchemaRelationship, SchemaTable
from app.repositories.mappers import (
    data_source_from_row,
    schema_column_from_row,
    schema_relationship_from_row,
    schema_table_from_row,
)
from app.schemas.requests import CreateSchemaRelationshipRequest, TableSelection
from app.services.adapter_factory import DataSourceFactory
from app.services.data_source_service import _get_row as get_data_source_row
from app.util.time import utc_now_iso


def _qualify_table(schema_name: str | None, table_name: str) -> str:
    return BaseDataSourceAdapter.qualify_table(schema_name, table_name)


def _object_key(
    schema_name: str | None,
    object_name: str,
    object_type: str = "table",
) -> tuple[str, str | None, str]:
    return (object_type, schema_name, object_name)


def _qualify_object(
    schema_name: str | None,
    object_name: str,
    object_type: str = "table",
) -> str:
    qualified = BaseDataSourceAdapter.qualify_table(schema_name, object_name)
    return f"{object_type}:{qualified}"


def _parse_qualified_object(name: str) -> tuple[str, str | None, str]:
    if ":" in name:
        object_type, rest = name.split(":", 1)
        if object_type in SCHEMA_OBJECT_TYPES:
            if "." in rest:
                schema, obj = rest.split(".", 1)
                return object_type, schema, obj
            return object_type, None, rest
    if "." in name:
        schema, obj = name.split(".", 1)
        return "table", schema, obj
    return "table", None, name


def import_schema_metadata(
    data_source_id: str,
    *,
    mode: str = "merge",
    include_tables: list[str] | None = None,
    exclude_tables: list[str] | None = None,
) -> dict[str, int]:
    """Introspect live DB and merge/replace persisted schema metadata."""
    if mode not in {"merge", "replace"}:
        raise ValidationAppError("mode must be 'merge' or 'replace'.")

    snapshot = introspect_schema_snapshot(data_source_id)
    drafts = list(snapshot.tables)

    if include_tables:
        include_keys = {_parse_qualified_object(name) for name in include_tables}
        drafts = [
            table
            for table in drafts
            if _object_key(
                table.schema_name,
                table.table_name,
                table.object_type,
            )
            in include_keys
        ]

    if exclude_tables:
        exclude_keys = {_parse_qualified_object(name) for name in exclude_tables}
        drafts = [
            table
            for table in drafts
            if _object_key(
                table.schema_name,
                table.table_name,
                table.object_type,
            )
            not in exclude_keys
        ]

    if not drafts:
        raise ValidationAppError("No schema objects matched the import selection.")

    if mode == "replace":
        existing_tables = SchemaTableRow.query.filter_by(data_source_id=data_source_id).all()
        for table_row in existing_tables:
            delete_table(data_source_id, table_row.id)

    selections = [
        TableSelection(
            schema_name=draft.schema_name,
            table_name=draft.table_name,
            object_type=draft.object_type,
        )
        for draft in drafts
    ]
    return onboard_selected_tables(data_source_id, selections)


def introspect_schema_snapshot(data_source_id: str) -> SchemaSnapshot:
    row = get_data_source_row(data_source_id)
    data_source = data_source_from_row(row)
    adapter = DataSourceFactory.get_adapter(data_source)
    return adapter.introspect_schema()


def onboard_selected_tables(
    data_source_id: str,
    selections: list[TableSelection],
) -> dict[str, int]:
    snapshot = introspect_schema_snapshot(data_source_id)
    selected_keys = {
        _object_key(sel.schema_name, sel.table_name, sel.object_type or "table")
        for sel in selections
    }
    drafts = [
        table
        for table in snapshot.tables
        if _object_key(table.schema_name, table.table_name, table.object_type) in selected_keys
    ]
    if not drafts:
        raise ValidationAppError("No matching schema objects found in the introspected schema.")

    tables_created = 0
    columns_created = 0
    relationships_created = 0

    table_id_by_key: dict[tuple[str, str | None, str], str] = {}
    column_id_by_qualified: dict[tuple[str, str], str] = {}

    for draft in drafts:
        table_id, col_count = _persist_table_draft(data_source_id, draft, table_id_by_key, column_id_by_qualified)
        tables_created += 1
        columns_created += col_count

    for draft in drafts:
        relationships_created += _persist_relationship_drafts(
            data_source_id,
            draft,
            table_id_by_key,
            column_id_by_qualified,
        )

    db.session.commit()
    return {
        "tables_imported": tables_created,
        "columns_imported": columns_created,
        "relationships_imported": relationships_created,
    }


def _persist_table_draft(
    data_source_id: str,
    draft: SchemaTableDraft,
    table_id_by_key: dict[tuple[str | None, str], str],
    column_id_by_qualified: dict[tuple[str, str], str],
) -> tuple[str, int]:
    key = _object_key(draft.schema_name, draft.table_name, draft.object_type)
    existing = SchemaTableRow.query.filter_by(
        data_source_id=data_source_id,
        schema_name=draft.schema_name,
        table_name=draft.table_name,
        object_type=draft.object_type,
    ).first()
    now = utc_now_iso()
    if existing:
        table_row = existing
        table_row.row_count_estimate = draft.row_count_estimate
        table_row.definition = draft.definition
        table_row.return_type = draft.return_type
        table_row.updated_at = now
        SchemaColumnRow.query.filter_by(table_id=table_row.id).delete()
    else:
        table_row = SchemaTableRow(
            id=str(uuid.uuid4()),
            data_source_id=data_source_id,
            schema_name=draft.schema_name,
            table_name=draft.table_name,
            object_type=draft.object_type,
            display_name=None,
            description=None,
            is_included_in_prompt=True,
            row_count_estimate=draft.row_count_estimate,
            definition=draft.definition,
            return_type=draft.return_type,
            created_at=now,
            updated_at=now,
        )
        db.session.add(table_row)

    table_id_by_key[key] = table_row.id
    qualified = _qualify_table(draft.schema_name, draft.table_name)
    col_count = 0
    for column in draft.columns:
        col_row = SchemaColumnRow(
            id=str(uuid.uuid4()),
            table_id=table_row.id,
            column_name=column.column_name,
            display_name=None,
            description=None,
            data_type=column.data_type,
            is_nullable=column.is_nullable,
            is_primary_key=column.is_primary_key,
            ordinal_position=column.ordinal_position,
            sample_distinct_values=column.sample_distinct_values,
            is_pii=False,
            is_excluded_from_prompt=False,
            created_at=now,
            updated_at=now,
        )
        db.session.add(col_row)
        column_id_by_qualified[(qualified, column.column_name)] = col_row.id
        col_count += 1
    return table_row.id, col_count


def _persist_relationship_drafts(
    data_source_id: str,
    draft: SchemaTableDraft,
    table_id_by_key: dict[tuple[str | None, str], str],
    column_id_by_qualified: dict[tuple[str, str], str],
) -> int:
    created = 0
    source_qualified = _qualify_table(draft.schema_name, draft.table_name)
    for rel in draft.relationships:
        source_col_id = column_id_by_qualified.get((source_qualified, rel.source_column))
        target_col_id = column_id_by_qualified.get((rel.target_table, rel.target_column))
        source_table_id = table_id_by_key.get(
            _object_key(draft.schema_name, draft.table_name, draft.object_type)
        )
        target_table_id = _resolve_table_id_by_name(data_source_id, rel.target_table, table_id_by_key)
        if not all([source_col_id, target_col_id, source_table_id, target_table_id]):
            continue
        existing = SchemaRelationshipRow.query.filter_by(
            data_source_id=data_source_id,
            constraint_name=rel.constraint_name,
        ).first()
        now = utc_now_iso()
        if existing:
            existing.source_table_id = source_table_id
            existing.source_column_id = source_col_id
            existing.target_table_id = target_table_id
            existing.target_column_id = target_col_id
            existing.relationship_type = rel.relationship_type
            existing.updated_at = now
        else:
            db.session.add(
                SchemaRelationshipRow(
                    id=str(uuid.uuid4()),
                    data_source_id=data_source_id,
                    constraint_name=rel.constraint_name,
                    source_table_id=source_table_id,
                    source_column_id=source_col_id,
                    target_table_id=target_table_id,
                    target_column_id=target_col_id,
                    relationship_type=rel.relationship_type,
                    created_at=now,
                    updated_at=now,
                )
            )
        created += 1
    return created


def _resolve_table_id_by_name(
    data_source_id: str,
    table_name: str,
    table_id_by_key: dict[tuple[str, str | None, str], str],
) -> str | None:
    for (object_type, schema_name, name), table_id in table_id_by_key.items():
        if object_type not in {"table", "view"}:
            continue
        if _qualify_table(schema_name, name) == table_name or name == table_name:
            return table_id
    row = SchemaTableRow.query.filter_by(
        data_source_id=data_source_id,
        table_name=table_name,
        object_type="table",
    ).first()
    if row:
        return row.id
    if "." in table_name:
        schema, name = table_name.split(".", 1)
        row = SchemaTableRow.query.filter_by(
            data_source_id=data_source_id,
            schema_name=schema,
            table_name=name,
            object_type="table",
        ).first()
        return row.id if row else None
    return None


def list_tables(data_source_id: str) -> list[SchemaTable]:
    get_data_source_row(data_source_id)
    rows = SchemaTableRow.query.filter_by(data_source_id=data_source_id).order_by(
        SchemaTableRow.table_name
    ).all()
    return [schema_table_from_row(row) for row in rows]


def get_table(data_source_id: str, table_id: str) -> SchemaTable:
    row = _get_table_row(data_source_id, table_id)
    return schema_table_from_row(row)


def update_table(
    data_source_id: str,
    table_id: str,
    *,
    display_name: str | None = None,
    description: str | None = None,
    is_included_in_prompt: bool | None = None,
) -> SchemaTable:
    row = _get_table_row(data_source_id, table_id)
    if display_name is not None:
        row.display_name = display_name
    if description is not None:
        row.description = description
    if is_included_in_prompt is not None:
        row.is_included_in_prompt = is_included_in_prompt
    row.updated_at = utc_now_iso()
    db.session.commit()
    return schema_table_from_row(row)


def delete_table(data_source_id: str, table_id: str) -> None:
    row = _get_table_row(data_source_id, table_id)
    SchemaColumnRow.query.filter_by(table_id=table_id).delete()
    SchemaRelationshipRow.query.filter(
        (SchemaRelationshipRow.source_table_id == table_id)
        | (SchemaRelationshipRow.target_table_id == table_id)
    ).delete()
    db.session.delete(row)
    db.session.commit()


def list_columns(data_source_id: str, table_id: str) -> list[SchemaColumn]:
    _get_table_row(data_source_id, table_id)
    rows = SchemaColumnRow.query.filter_by(table_id=table_id).order_by(
        SchemaColumnRow.ordinal_position
    ).all()
    return [schema_column_from_row(row) for row in rows]


def update_column(
    data_source_id: str,
    column_id: str,
    *,
    display_name: str | None = None,
    description: str | None = None,
    is_pii: bool | None = None,
    is_excluded_from_prompt: bool | None = None,
) -> SchemaColumn:
    row = _get_column_row(data_source_id, column_id)
    if display_name is not None:
        row.display_name = display_name
    if description is not None:
        row.description = description
    if is_pii is not None:
        row.is_pii = is_pii
    if is_excluded_from_prompt is not None:
        row.is_excluded_from_prompt = is_excluded_from_prompt
    row.updated_at = utc_now_iso()
    db.session.commit()
    return schema_column_from_row(row)


def list_relationships(data_source_id: str) -> list[SchemaRelationship]:
    get_data_source_row(data_source_id)
    rows = SchemaRelationshipRow.query.filter_by(data_source_id=data_source_id).all()
    return [schema_relationship_from_row(row) for row in rows]


def create_relationship(
    data_source_id: str,
    payload: CreateSchemaRelationshipRequest,
) -> SchemaRelationship:
    get_data_source_row(data_source_id)
    _get_table_row(data_source_id, payload.source_table_id)
    _get_table_row(data_source_id, payload.target_table_id)
    _get_column_row(data_source_id, payload.source_column_id)
    _get_column_row(data_source_id, payload.target_column_id)
    now = utc_now_iso()
    row = SchemaRelationshipRow(
        id=str(uuid.uuid4()),
        data_source_id=data_source_id,
        constraint_name=payload.constraint_name,
        source_table_id=payload.source_table_id,
        source_column_id=payload.source_column_id,
        target_table_id=payload.target_table_id,
        target_column_id=payload.target_column_id,
        relationship_type=payload.relationship_type,
        created_at=now,
        updated_at=now,
    )
    db.session.add(row)
    db.session.commit()
    return schema_relationship_from_row(row)


def delete_relationship(data_source_id: str, relationship_id: str) -> None:
    row = db.session.get(SchemaRelationshipRow, relationship_id)
    if row is None or row.data_source_id != data_source_id:
        raise NotFoundError(f"Relationship {relationship_id} not found.")
    db.session.delete(row)
    db.session.commit()


def _get_table_row(data_source_id: str, table_id: str) -> SchemaTableRow:
    row = db.session.get(SchemaTableRow, table_id)
    if row is None or row.data_source_id != data_source_id:
        raise NotFoundError(f"Table {table_id} not found.")
    return row


def _get_column_row(data_source_id: str, column_id: str) -> SchemaColumnRow:
    row = db.session.get(SchemaColumnRow, column_id)
    if row is None:
        raise NotFoundError(f"Column {column_id} not found.")
    table_row = db.session.get(SchemaTableRow, row.table_id)
    if table_row is None or table_row.data_source_id != data_source_id:
        raise NotFoundError(f"Column {column_id} not found.")
    return row
