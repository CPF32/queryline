"""Admin glossary endpoints."""

from flask import Blueprint, request

from app.api.responses import list_response, success_response
from app.api.validation import parse_json
from app.schemas.requests import CreateGlossaryTermRequest, UpdateGlossaryTermRequest
from app.services import glossary_service

admin_glossary_bp = Blueprint("admin_glossary", __name__)


@admin_glossary_bp.get("/data-sources/<data_source_id>/glossary")
def list_terms(data_source_id: str):
    terms = glossary_service.list_terms(data_source_id)
    return list_response([term.to_dict() for term in terms], total=len(terms))


@admin_glossary_bp.post("/data-sources/<data_source_id>/glossary")
def create_term(data_source_id: str):
    body = parse_json(request, CreateGlossaryTermRequest)
    term = glossary_service.create_term(
        data_source_id,
        term=body.term,
        definition=body.definition,
        sql_expression=body.sql_expression,
        table_id=body.table_id,
        column_id=body.column_id,
    )
    return success_response(term.to_dict(), status=201)


@admin_glossary_bp.get("/data-sources/<data_source_id>/glossary/<term_id>")
def get_term(data_source_id: str, term_id: str):
    term = glossary_service.get_term(data_source_id, term_id)
    return success_response(term.to_dict())


@admin_glossary_bp.put("/data-sources/<data_source_id>/glossary/<term_id>")
def update_term(data_source_id: str, term_id: str):
    body = parse_json(request, UpdateGlossaryTermRequest)
    term = glossary_service.update_term(
        data_source_id,
        term_id,
        term=body.term,
        definition=body.definition,
        sql_expression=body.sql_expression,
        table_id=body.table_id,
        column_id=body.column_id,
    )
    return success_response(term.to_dict())


@admin_glossary_bp.delete("/data-sources/<data_source_id>/glossary/<term_id>")
def delete_term(data_source_id: str, term_id: str):
    glossary_service.delete_term(data_source_id, term_id)
    return "", 204
