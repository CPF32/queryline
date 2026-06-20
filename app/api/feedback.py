"""Query feedback endpoints."""

from __future__ import annotations

from flask import Blueprint, request

from app.api.responses import success_response
from app.api.validation import parse_json
from app.auth.context import require_user
from app.schemas.feedback import SubmitFeedbackRequest
from app.services import feedback_service

feedback_bp = Blueprint("feedback", __name__)


@feedback_bp.post("/query-log/<entry_id>/feedback")
def submit_feedback(entry_id: str):
    user = require_user()
    body = parse_json(request, SubmitFeedbackRequest)
    feedback = feedback_service.submit_feedback(
        query_log_id=entry_id,
        user_id=user.id,
        rating=body.rating,
        comment=body.comment,
    )
    return success_response(feedback.to_dict(), status=201)


@feedback_bp.get("/query-log/<entry_id>/feedback")
def get_feedback(entry_id: str):
    user = require_user()
    feedback = feedback_service.get_feedback_for_entry(entry_id, user_id=user.id)
    return success_response(feedback.to_dict() if feedback else None)
