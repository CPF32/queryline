"""Admin SQL example endpoints."""

from flask import Blueprint, request

from app.api.responses import list_response, success_response
from app.api.validation import parse_json
from app.schemas.requests import CreateSqlExampleRequest, UpdateSqlExampleRequest
from app.services import examples_service

admin_examples_bp = Blueprint("admin_examples", __name__)


@admin_examples_bp.get("/data-sources/<data_source_id>/examples")
def list_examples(data_source_id: str):
    examples = examples_service.list_examples(data_source_id)
    return list_response([example.to_dict() for example in examples], total=len(examples))


@admin_examples_bp.post("/data-sources/<data_source_id>/examples")
def create_example(data_source_id: str):
    body = parse_json(request, CreateSqlExampleRequest)
    example = examples_service.create_example(
        data_source_id,
        question=body.question,
        sql=body.sql,
        notes=body.notes,
    )
    return success_response(example.to_dict(), status=201)


@admin_examples_bp.get("/data-sources/<data_source_id>/examples/<example_id>")
def get_example(data_source_id: str, example_id: str):
    example = examples_service.get_example(data_source_id, example_id)
    return success_response(example.to_dict())


@admin_examples_bp.put("/data-sources/<data_source_id>/examples/<example_id>")
def update_example(data_source_id: str, example_id: str):
    body = parse_json(request, UpdateSqlExampleRequest)
    example = examples_service.update_example(
        data_source_id,
        example_id,
        question=body.question,
        sql=body.sql,
        notes=body.notes,
    )
    return success_response(example.to_dict())


@admin_examples_bp.delete("/data-sources/<data_source_id>/examples/<example_id>")
def delete_example(data_source_id: str, example_id: str):
    examples_service.delete_example(data_source_id, example_id)
    return "", 204
