"""ORM row to domain model mappers."""

from app.db import (
    DataSourceRow,
    GlossaryTermRow,
    QueryLogEntryRow,
    SchemaColumnRow,
    SchemaRelationshipRow,
    SchemaTableRow,
    SqlExampleRow,
)
from app.models.data_source import DataSource
from app.models.glossary import GlossaryTerm
from app.models.query_log import QueryLogEntry
from app.models.schema import SchemaColumn, SchemaRelationship, SchemaTable
from app.models.sql_example import SqlExample


def data_source_from_row(row: DataSourceRow) -> DataSource:
    return DataSource(
        id=row.id,
        name=row.name,
        connector_type=row.connector_type,
        connection_config=row.connection_config,
        is_active=row.is_active,
        dialect_name=row.dialect_name,
        created_at=row.created_at,
        updated_at=row.updated_at,
        user_id=row.user_id,
        workspace_id=row.workspace_id,
    )


def schema_table_from_row(row: SchemaTableRow) -> SchemaTable:
    return SchemaTable(
        id=row.id,
        data_source_id=row.data_source_id,
        schema_name=row.schema_name,
        table_name=row.table_name,
        object_type=getattr(row, "object_type", None) or "table",
        display_name=row.display_name,
        description=row.description,
        is_included_in_prompt=row.is_included_in_prompt,
        row_count_estimate=row.row_count_estimate,
        definition=getattr(row, "definition", None),
        return_type=getattr(row, "return_type", None),
        created_at=row.created_at,
        updated_at=row.updated_at,
        user_id=row.user_id,
        workspace_id=row.workspace_id,
    )


def schema_column_from_row(row: SchemaColumnRow) -> SchemaColumn:
    return SchemaColumn(
        id=row.id,
        table_id=row.table_id,
        column_name=row.column_name,
        display_name=row.display_name,
        description=row.description,
        data_type=row.data_type,
        is_nullable=row.is_nullable,
        is_primary_key=row.is_primary_key,
        ordinal_position=row.ordinal_position,
        sample_distinct_values=row.sample_distinct_values,
        is_pii=row.is_pii,
        is_excluded_from_prompt=row.is_excluded_from_prompt,
        created_at=row.created_at,
        updated_at=row.updated_at,
        user_id=row.user_id,
        workspace_id=row.workspace_id,
    )


def schema_relationship_from_row(row: SchemaRelationshipRow) -> SchemaRelationship:
    return SchemaRelationship(
        id=row.id,
        data_source_id=row.data_source_id,
        constraint_name=row.constraint_name,
        source_table_id=row.source_table_id,
        source_column_id=row.source_column_id,
        target_table_id=row.target_table_id,
        target_column_id=row.target_column_id,
        relationship_type=row.relationship_type,
        created_at=row.created_at,
        updated_at=row.updated_at,
        user_id=row.user_id,
        workspace_id=row.workspace_id,
    )


def glossary_term_from_row(row: GlossaryTermRow) -> GlossaryTerm:
    return GlossaryTerm(
        id=row.id,
        data_source_id=row.data_source_id,
        term=row.term,
        definition=row.definition,
        sql_expression=row.sql_expression,
        table_id=row.table_id,
        column_id=row.column_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        user_id=row.user_id,
        workspace_id=row.workspace_id,
    )


def sql_example_from_row(row: SqlExampleRow) -> SqlExample:
    return SqlExample(
        id=row.id,
        data_source_id=row.data_source_id,
        question=row.question,
        sql=row.sql,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
        user_id=row.user_id,
        workspace_id=row.workspace_id,
    )


def query_log_from_row(row: QueryLogEntryRow) -> QueryLogEntry:
    return QueryLogEntry(
        id=row.id,
        data_source_id=row.data_source_id,
        session_id=row.session_id,
        user_question=row.user_question,
        generated_sql=row.generated_sql,
        execution_status=row.execution_status,
        error_message=row.error_message,
        row_count=row.row_count,
        execution_ms=row.execution_ms,
        chart_spec=row.chart_spec,
        created_at=row.created_at,
        user_id=row.user_id,
        workspace_id=row.workspace_id,
    )
