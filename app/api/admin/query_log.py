"""Admin query log endpoints."""

from flask import Blueprint, request

from app.api.responses import list_response, success_response
from app.api.validation import parse_json
from app.schemas.requests import PromoteQueryLogRequest
from app.services import query_log_service

admin_query_log_bp = Blueprint("admin_query_log", __name__)


@admin_query_log_bp.get("/data-sources/<data_source_id>/query-log")
def list_query_log_for_source(data_source_id: str):
    session_id = request.args.get("session_id")
    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)
    entries, total = query_log_service.list_query_log(
        data_source_id=data_source_id,
        execution_status=None,
        limit=limit,
        offset=offset,
    )
    if session_id:
        entries = [entry for entry in entries if entry.session_id == session_id]
        total = len(entries)
    return list_response(
        [entry.to_dict() for entry in entries],
        total=total,
        limit=limit,
        offset=offset,
    )


@admin_query_log_bp.get("/query-log")
def list_query_log():
    data_source_id = request.args.get("data_source_id")
    execution_status = request.args.get("execution_status")
    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)
    entries, total = query_log_service.list_query_log(
        data_source_id=data_source_id,
        execution_status=execution_status,
        limit=limit,
        offset=offset,
    )
    return list_response(
        [entry.to_dict() for entry in entries],
        total=total,
        limit=limit,
        offset=offset,
    )


@admin_query_log_bp.get("/query-log/<entry_id>")
def get_query_log_entry(entry_id: str):
    entry = query_log_service.get_query_log_entry(entry_id)
    return success_response(entry.to_dict())


@admin_query_log_bp.post("/query-log/<entry_id>/promote-to-example")
def promote_to_example(entry_id: str):
    body = parse_json(request, PromoteQueryLogRequest)
    example = query_log_service.promote_to_example(entry_id, notes=body.notes)
    return success_response(example.to_dict(), status=201)
