"""Persistent diagnostic log for developer troubleshooting."""

from __future__ import annotations

import traceback
import uuid
from typing import Any

from app.db import DiagnosticLogRow, db
from app.util.time import utc_now_iso

MAX_ENTRIES = 1000


def _trim_old_entries() -> None:
    total = DiagnosticLogRow.query.count()
    if total <= MAX_ENTRIES:
        return
    overflow = total - MAX_ENTRIES
    oldest = (
        DiagnosticLogRow.query.order_by(DiagnosticLogRow.created_at.asc())
        .limit(overflow)
        .all()
    )
    for row in oldest:
        db.session.delete(row)


def log_event(
    *,
    level: str,
    source: str,
    message: str,
    details: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> None:
    row = DiagnosticLogRow(
        id=str(uuid.uuid4()),
        level=level,
        source=source,
        message=message[:4000],
        details=details,
        user_id=user_id,
        created_at=utc_now_iso(),
    )
    db.session.add(row)
    db.session.commit()
    _trim_old_entries()


def log_error(
    source: str,
    message: str,
    *,
    exc: BaseException | None = None,
    details: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> None:
    payload = dict(details or {})
    if exc is not None:
        payload.setdefault("exception_type", type(exc).__name__)
        payload.setdefault("traceback", traceback.format_exc())
    try:
        log_event(
            level="error",
            source=source,
            message=message,
            details=payload or None,
            user_id=user_id,
        )
    except Exception:
        db.session.rollback()


def list_logs(
    *,
    limit: int = 50,
    offset: int = 0,
    level: str | None = None,
    source: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    query = DiagnosticLogRow.query
    if level:
        query = query.filter_by(level=level)
    if source:
        query = query.filter(DiagnosticLogRow.source == source)
    total = query.count()
    rows = (
        query.order_by(DiagnosticLogRow.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_row_to_dict(row) for row in rows], total


def clear_logs() -> int:
    deleted = DiagnosticLogRow.query.delete()
    db.session.commit()
    return deleted


def _row_to_dict(row: DiagnosticLogRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "level": row.level,
        "source": row.source,
        "message": row.message,
        "details": row.details,
        "user_id": row.user_id,
        "created_at": row.created_at,
    }
