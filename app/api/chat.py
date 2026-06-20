"""Chat, SQL generation, execution, and chart-spec REST endpoints.

Endpoints:
    POST   /api/v1/chat/generate-sql
    POST   /api/v1/chat/generate-sql/stream
    POST   /api/v1/chat/execute
    POST   /api/v1/chat/generate-and-execute
    POST   /api/v1/chat/chart-spec
    POST   /api/v1/chat/transcribe

See CONTRACTS.md §5.8–§5.10.
"""

from __future__ import annotations

import json

from flask import Blueprint, request, Response, stream_with_context

from app.api.responses import error_response, success_response
from app.api.validation import parse_json
from app.auth.context import require_user
from app.db import db
from app.errors import ValidationAppError
from app.schemas.chat_requests import (
    ChartSpecRequest,
    ExecuteQueryRequest,
    GenerateAndExecuteRequest,
    GenerateSqlRequest,
)
from app.services import (
    chart_spec_service,
    query_execution_service,
    speech_transcription_service,
    sql_generation_service,
)
chat_bp = Blueprint("chat", __name__)

_MAX_TRANSCRIBE_BYTES = 10 * 1024 * 1024


@chat_bp.post("/chat/generate-sql")
def generate_sql():
    require_user()
    body = parse_json(request, GenerateSqlRequest)
    history = [message.model_dump() for message in body.conversation_history]
    result = sql_generation_service.generate_sql(
        body.question,
        body.data_source_id,
        conversation_history=history,
        retry_context=body.retry_context,
    )
    if not result.success:
        return error_response(
            "sql_generation_failed",
            result.error_message or result.explanation,
            status=422,
            details={
                "explanation": result.explanation,
                "attempt_number": result.attempt_number,
                "matched_glossary_terms": result.matched_glossary_terms,
            },
        )
    return success_response(
        {
            "sql": result.sql,
            "explanation": result.explanation,
            "tables_referenced": result.tables_used,
            "confidence": result.confidence,
            "chart_hint": result.chart_hint,
            "attempt_number": result.attempt_number,
        }
    )


@chat_bp.post("/chat/generate-sql/stream")
def generate_sql_stream():
    require_user()
    body = parse_json(request, GenerateSqlRequest)
    history = [message.model_dump() for message in body.conversation_history]

    def event_stream():
        for event in sql_generation_service.stream_generate_sql(
            body.question,
            body.data_source_id,
            conversation_history=history,
            retry_context=body.retry_context,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        direct_passthrough=True,
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream; charset=utf-8",
        },
    )


@chat_bp.post("/chat/execute")
def execute_query():
    user = require_user()
    body = parse_json(request, ExecuteQueryRequest)
    try:
        query_result, query_log_id = query_execution_service.execute_query(
            data_source_id=body.data_source_id,
            session_id=body.session_id,
            sql=body.sql,
            user_question=body.user_question,
            max_rows=body.max_rows,
            timeout_seconds=body.timeout_seconds,
            user_id=user.id,
            conversation_id=body.conversation_id,
        )
    except ValidationAppError as exc:
        details = exc.details if isinstance(exc.details, dict) else {"details": exc.details}
        return error_response(exc.code, exc.message, status=exc.status_code, details=details)

    return success_response(
        {
            "query_result": query_result.to_dict(),
            "query_log_id": query_log_id,
        }
    )


@chat_bp.post("/chat/generate-and-execute")
def generate_and_execute_query():
    user = require_user()
    body = parse_json(request, GenerateAndExecuteRequest)
    outcome = query_execution_service.generate_and_execute(
        data_source_id=body.data_source_id,
        session_id=body.session_id,
        question=body.question,
        conversation_history=[message.model_dump() for message in body.conversation_history],
        max_rows=body.max_rows,
        timeout_seconds=body.timeout_seconds,
    )

    if outcome.success:
        assert outcome.query_result is not None
        return success_response(
            {
                "success": True,
                "sql": outcome.sql,
                "explanation": outcome.explanation,
                "confidence": outcome.confidence,
                "tables_used": outcome.tables_used or [],
                "attempts": outcome.attempts,
                "query_result": outcome.query_result.to_dict(),
                "query_log_id": outcome.query_log_id,
            }
        )

    return error_response(
        "query_failed",
        outcome.error_message or "Query could not be generated and executed.",
        status=422,
        details={
            "success": False,
            "sql": outcome.sql,
            "attempts": outcome.attempts,
            "error_category": outcome.error_category,
            "query_log_id": outcome.query_log_id,
        },
    )


@chat_bp.post("/chat/chart-spec")
def chart_spec():
    require_user()
    body = parse_json(request, ChartSpecRequest)
    sample_rows = [
        {
            column.name: row[index]
            for index, column in enumerate(body.query_result.columns)
        }
        for row in body.query_result.rows
    ]
    spec = chart_spec_service.generate_chart_spec(
        columns=body.query_result.columns,
        sample_rows=sample_rows,
        row_count=body.query_result.row_count,
        original_question=body.user_question,
        chart_hint=body.chart_hint,
    )

    if body.query_log_id:
        from app.db import QueryLogEntryRow

        row = db.session.get(QueryLogEntryRow, body.query_log_id)
        if row is not None and row.data_source_id == body.data_source_id:
            row.chart_spec = spec.to_dict()
            db.session.commit()

    return success_response({"chart_spec": spec.to_dict()})


@chat_bp.post("/chat/transcribe")
def transcribe_speech():
    require_user()
    upload = request.files.get("audio")
    if upload is None:
        return error_response(
            "validation_error",
            "Missing audio file.",
            status=422,
            details=None,
        )

    audio_bytes = upload.read()
    if not audio_bytes:
        return error_response(
            "validation_error",
            "Audio file is empty.",
            status=422,
            details=None,
        )
    if len(audio_bytes) > _MAX_TRANSCRIBE_BYTES:
        return error_response(
            "validation_error",
            "Audio file is too large.",
            status=422,
            details=None,
        )

    try:
        text = speech_transcription_service.transcribe_audio(
            audio_bytes=audio_bytes,
            mime_type=upload.mimetype or "application/octet-stream",
        )
    except RuntimeError as exc:
        return error_response(
            "transcription_failed",
            str(exc),
            status=422,
            details=None,
        )

    return success_response({"text": text})
