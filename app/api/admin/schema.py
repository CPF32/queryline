"""Admin schema import and metadata endpoints."""

from flask import Blueprint, request

from app.api.responses import list_response, success_response
from app.api.validation import parse_json
from app.schemas.requests import (
    CreateSchemaRelationshipRequest,
    ImportSchemaRequest,
    OnboardSchemaTablesRequest,
    UpdateSchemaColumnRequest,
    UpdateSchemaTableRequest,
)
from app.services import metadata_service, schema_service

admin_schema_bp = Blueprint("admin_schema", __name__)


@admin_schema_bp.post("/data-sources/<data_source_id>/import-schema")
def import_schema_preview(data_source_id: str):
    snapshot = schema_service.introspect_schema_snapshot(data_source_id)
    return success_response(snapshot.to_dict())


@admin_schema_bp.post("/data-sources/<data_source_id>/schema/introspect")
def introspect_schema(data_source_id: str):
    snapshot = schema_service.introspect_schema_snapshot(data_source_id)
    return success_response(snapshot.to_dict())


@admin_schema_bp.post("/data-sources/<data_source_id>/schema/import")
def import_schema(data_source_id: str):
    body = parse_json(request, ImportSchemaRequest)
    result = schema_service.import_schema_metadata(
        data_source_id,
        mode=body.mode,
        include_tables=body.include_tables,
        exclude_tables=body.exclude_tables,
    )
    return success_response(result)


@admin_schema_bp.post("/data-sources/<data_source_id>/schema-tables")
def onboard_schema_tables(data_source_id: str):
    body = parse_json(request, OnboardSchemaTablesRequest)
    result = schema_service.onboard_selected_tables(data_source_id, body.tables)
    return success_response(result)


@admin_schema_bp.get("/data-sources/<data_source_id>/metadata-bundle")
def metadata_bundle(data_source_id: str):
    bundle = metadata_service.build_metadata_bundle(data_source_id)
    return success_response(bundle.to_dict())


@admin_schema_bp.get("/data-sources/<data_source_id>/schema/tables")
def list_tables(data_source_id: str):
    tables = schema_service.list_tables(data_source_id)
    return list_response([table.to_dict() for table in tables], total=len(tables))


@admin_schema_bp.get("/data-sources/<data_source_id>/schema/tables/<table_id>")
def get_table(data_source_id: str, table_id: str):
    table = schema_service.get_table(data_source_id, table_id)
    return success_response(table.to_dict())


@admin_schema_bp.put("/data-sources/<data_source_id>/schema/tables/<table_id>")
def update_table(data_source_id: str, table_id: str):
    body = parse_json(request, UpdateSchemaTableRequest)
    table = schema_service.update_table(
        data_source_id,
        table_id,
        display_name=body.display_name,
        description=body.description,
        is_included_in_prompt=body.is_included_in_prompt,
    )
    return success_response(table.to_dict())


@admin_schema_bp.delete("/data-sources/<data_source_id>/schema/tables/<table_id>")
def delete_table(data_source_id: str, table_id: str):
    schema_service.delete_table(data_source_id, table_id)
    return "", 204


@admin_schema_bp.get("/data-sources/<data_source_id>/schema/tables/<table_id>/columns")
def list_columns(data_source_id: str, table_id: str):
    columns = schema_service.list_columns(data_source_id, table_id)
    return list_response([column.to_dict() for column in columns], total=len(columns))


@admin_schema_bp.put("/data-sources/<data_source_id>/schema/columns/<column_id>")
def update_column(data_source_id: str, column_id: str):
    body = parse_json(request, UpdateSchemaColumnRequest)
    column = schema_service.update_column(
        data_source_id,
        column_id,
        display_name=body.display_name,
        description=body.description,
        is_pii=body.is_pii,
        is_excluded_from_prompt=body.is_excluded_from_prompt,
    )
    return success_response(column.to_dict())


@admin_schema_bp.get("/data-sources/<data_source_id>/schema/relationships")
def list_relationships(data_source_id: str):
    relationships = schema_service.list_relationships(data_source_id)
    return list_response(
        [relationship.to_dict() for relationship in relationships],
        total=len(relationships),
    )


@admin_schema_bp.post("/data-sources/<data_source_id>/schema/relationships")
def create_relationship(data_source_id: str):
    body = parse_json(request, CreateSchemaRelationshipRequest)
    relationship = schema_service.create_relationship(data_source_id, body)
    return success_response(relationship.to_dict(), status=201)


@admin_schema_bp.delete("/data-sources/<data_source_id>/schema/relationships/<relationship_id>")
def delete_relationship(data_source_id: str, relationship_id: str):
    schema_service.delete_relationship(data_source_id, relationship_id)
    return "", 204
