"""Assemble curated metadata bundle for SQL generation."""

from __future__ import annotations

from app.adapters._common import BaseDataSourceAdapter
from app.db import (
    GlossaryTermRow,
    SchemaColumnRow,
    SchemaRelationshipRow,
    SchemaTableRow,
    SqlExampleRow,
)
from app.repositories.mappers import data_source_from_row
from app.schemas.metadata_bundle import (
    MetadataBundle,
    MetadataBundleColumn,
    MetadataBundleExample,
    MetadataBundleGlossaryTerm,
    MetadataBundleRelationship,
    MetadataBundleTable,
)
from app.services.data_source_service import _get_row


def build_metadata_bundle(data_source_id: str) -> MetadataBundle:
    ds_row = _get_row(data_source_id)
    data_source = data_source_from_row(ds_row)

    table_rows = SchemaTableRow.query.filter_by(
        data_source_id=data_source_id,
        is_included_in_prompt=True,
    ).order_by(SchemaTableRow.table_name).all()

    table_by_id = {row.id: row for row in table_rows}
    column_rows: list[SchemaColumnRow] = []
    if table_by_id:
        column_rows = (
            SchemaColumnRow.query.filter(
                SchemaColumnRow.table_id.in_(table_by_id.keys()),
                SchemaColumnRow.is_excluded_from_prompt.is_(False),
            )
            .order_by(SchemaColumnRow.ordinal_position)
            .all()
        )

    columns_by_table: dict[str, list[SchemaColumnRow]] = {}
    column_by_id: dict[str, SchemaColumnRow] = {}
    for col in column_rows:
        columns_by_table.setdefault(col.table_id, []).append(col)
        column_by_id[col.id] = col

    bundle_tables: list[MetadataBundleTable] = []
    for table_row in table_rows:
        qualified = BaseDataSourceAdapter.qualify_table(table_row.schema_name, table_row.table_name)
        bundle_columns = []
        for col in columns_by_table.get(table_row.id, []):
            samples = None if col.is_pii else col.sample_distinct_values
            bundle_columns.append(
                MetadataBundleColumn(
                    id=col.id,
                    name=col.column_name,
                    display_name=col.display_name,
                    description=col.description,
                    data_type=col.data_type,
                    is_nullable=col.is_nullable,
                    is_primary_key=col.is_primary_key,
                    is_pii=col.is_pii,
                    is_excluded_from_prompt=col.is_excluded_from_prompt,
                    sample_distinct_values=samples,
                )
            )
        bundle_tables.append(
            MetadataBundleTable(
                id=table_row.id,
                schema_name=table_row.schema_name,
                table_name=table_row.table_name,
                qualified_name=qualified,
                object_type=getattr(table_row, "object_type", None) or "table",
                display_name=table_row.display_name,
                description=table_row.description,
                row_count_estimate=table_row.row_count_estimate,
                definition=getattr(table_row, "definition", None),
                return_type=getattr(table_row, "return_type", None),
                columns=bundle_columns,
            )
        )

    rel_rows = SchemaRelationshipRow.query.filter_by(data_source_id=data_source_id).all()
    relationships: list[MetadataBundleRelationship] = []
    for rel in rel_rows:
        source_table = table_by_id.get(rel.source_table_id)
        target_table = table_by_id.get(rel.target_table_id)
        source_col = column_by_id.get(rel.source_column_id)
        target_col = column_by_id.get(rel.target_column_id)
        if not all([source_table, target_table, source_col, target_col]):
            continue
        relationships.append(
            MetadataBundleRelationship(
                id=rel.id,
                constraint_name=rel.constraint_name,
                source_table=BaseDataSourceAdapter.qualify_table(
                    source_table.schema_name, source_table.table_name
                ),
                source_column=source_col.column_name,
                target_table=BaseDataSourceAdapter.qualify_table(
                    target_table.schema_name, target_table.table_name
                ),
                target_column=target_col.column_name,
                relationship_type=rel.relationship_type,
            )
        )

    glossary_rows = GlossaryTermRow.query.filter_by(data_source_id=data_source_id).order_by(
        GlossaryTermRow.term
    ).all()
    glossary: list[MetadataBundleGlossaryTerm] = []
    for term in glossary_rows:
        table_name = None
        column_name = None
        if term.table_id and term.table_id in table_by_id:
            table_name = BaseDataSourceAdapter.qualify_table(
                table_by_id[term.table_id].schema_name,
                table_by_id[term.table_id].table_name,
            )
        if term.column_id and term.column_id in column_by_id:
            column_name = column_by_id[term.column_id].column_name
        glossary.append(
            MetadataBundleGlossaryTerm(
                id=term.id,
                term=term.term,
                definition=term.definition,
                sql_expression=term.sql_expression,
                table_id=term.table_id,
                column_id=term.column_id,
                table_name=table_name,
                column_name=column_name,
            )
        )

    example_rows = SqlExampleRow.query.filter_by(data_source_id=data_source_id).order_by(
        SqlExampleRow.created_at.desc()
    ).all()
    examples = [
        MetadataBundleExample(
            id=row.id,
            question=row.question,
            sql=row.sql,
            notes=row.notes,
            source=getattr(row, "source", None) or "manual",
        )
        for row in example_rows
    ]

    return MetadataBundle(
        data_source_id=data_source.id,
        data_source_name=data_source.name,
        dialect_name=data_source.dialect_name,
        tables=bundle_tables,
        relationships=relationships,
        glossary=glossary,
        examples=examples,
    )
