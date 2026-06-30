"""Developer diagnostic log API."""

from __future__ import annotations

from flask import Blueprint, request

from app.api.responses import list_response, success_response
from app.api.validation import parse_json
from app.auth.context import require_developer, require_user
from app.schemas.diagnostic_logs import CreateDiagnosticEventRequest
from app.services import diagnostic_log_service

admin_diagnostic_logs_bp = Blueprint("admin_diagnostic_logs", __name__)
diagnostic_events_bp = Blueprint("diagnostic_events", __name__)


@admin_diagnostic_logs_bp.get("/diagnostic-logs")
def list_diagnostic_logs():
    require_developer()
    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)
    level = request.args.get("level", default=None, type=str)
    source = request.args.get("source", default=None, type=str)
    entries, total = diagnostic_log_service.list_logs(
        limit=limit,
        offset=offset,
        level=level,
        source=source,
    )
    return list_response(entries, total=total, limit=limit, offset=offset)


@admin_diagnostic_logs_bp.delete("/diagnostic-logs")
def clear_diagnostic_logs():
    require_developer()
    deleted = diagnostic_log_service.clear_logs()
    return success_response({"deleted": deleted})


@diagnostic_events_bp.post("/diagnostic-events")
def create_diagnostic_event():
    user = require_user()
    body = parse_json(request, CreateDiagnosticEventRequest)
    diagnostic_log_service.log_event(
        level=body.level,
        source=f"client:{body.source}",
        message=body.message,
        details=body.details,
        user_id=user.id,
    )
    return "", 204
