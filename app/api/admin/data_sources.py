"""Admin data source endpoints."""

from flask import Blueprint, request

from app.api.responses import list_response, success_response
from app.api.validation import parse_json
from app.schemas.requests import CreateDataSourceRequest, TestConnectionRequest, UpdateDataSourceRequest
from app.services import data_source_service
from app.services.adapter_factory import DataSourceFactory

admin_data_sources_bp = Blueprint("admin_data_sources", __name__)


@admin_data_sources_bp.get("/connectors")
def list_connectors():
    return success_response(DataSourceFactory.list_connectors())


@admin_data_sources_bp.get("/data-sources")
def list_data_sources():
    sources = data_source_service.list_data_sources()
    return list_response(
        [source.to_dict() for source in sources],
        total=len(sources),
    )


@admin_data_sources_bp.get("/data-sources/<data_source_id>")
def get_data_source(data_source_id: str):
    source = data_source_service.get_data_source(data_source_id)
    return success_response(source.to_dict())


@admin_data_sources_bp.post("/data-sources")
def create_data_source():
    body = parse_json(request, CreateDataSourceRequest)
    source = data_source_service.create_data_source(
        name=body.name,
        connector_type=body.resolved_connector_type(),
        connection_config=body.connection_config,
        is_active=body.is_active,
    )
    return success_response(source.to_dict(), status=201)


@admin_data_sources_bp.put("/data-sources/<data_source_id>")
def update_data_source(data_source_id: str):
    body = parse_json(request, UpdateDataSourceRequest)
    source = data_source_service.update_data_source(
        data_source_id,
        name=body.name,
        connector_type=body.resolved_connector_type(),
        connection_config=body.connection_config,
        is_active=body.is_active,
    )
    return success_response(source.to_dict())


@admin_data_sources_bp.delete("/data-sources/<data_source_id>")
def delete_data_source(data_source_id: str):
    data_source_service.delete_data_source(data_source_id)
    return "", 204


@admin_data_sources_bp.post("/data-sources/test-connection")
def test_connection_unsaved():
    body = parse_json(request, TestConnectionRequest)
    result = data_source_service.test_connection_for_config(
        body.resolved_connector_type(),
        body.connection_config,
    )
    return success_response(result.to_dict())


@admin_data_sources_bp.get("/connectors/<connector_type>/connection-form-schema")
def connector_form_schema(connector_type: str):
    schema = DataSourceFactory.connection_form_schema(connector_type)
    return success_response(schema)


@admin_data_sources_bp.post("/data-sources/<data_source_id>/test-connection")
def test_saved_connection_contract(data_source_id: str):
    result = data_source_service.test_saved_connection(data_source_id)
    return success_response(result.to_dict())


@admin_data_sources_bp.post("/data-sources/<data_source_id>/test")
def test_saved_connection(data_source_id: str):
    result = data_source_service.test_saved_connection(data_source_id)
    return success_response(result.to_dict())


@admin_data_sources_bp.get("/data-sources/<data_source_id>/connection-form-schema")
def connection_form_schema(data_source_id: str):
    source = data_source_service.get_data_source(data_source_id)
    schema = DataSourceFactory.connection_form_schema(source.connector_type)
    return success_response(schema)
