"""User feedback on query responses and learning loop."""

from __future__ import annotations

import uuid

from app.db import QueryFeedbackRow, QueryLogEntryRow, SqlExampleRow, db
from app.models.feedback import FeedbackRating, QueryFeedback
from app.services.examples_service import create_example
from app.services.metadata_retrieval import _cosine, _embed
from app.services.query_log_service import get_query_log_entry
from app.util.time import utc_now_iso


def _feedback_from_row(row: QueryFeedbackRow) -> QueryFeedback:
    return QueryFeedback(
        id=row.id,
        query_log_id=row.query_log_id,
        user_id=row.user_id,
        rating=row.rating,  # type: ignore[arg-type]
        comment=row.comment,
        created_at=row.created_at,
    )


def _question_similarity(left: str, right: str) -> float:
    return _cosine(_embed(left), _embed(right))


def _has_similar_example(data_source_id: str, question: str) -> bool:
    rows = SqlExampleRow.query.filter_by(data_source_id=data_source_id).all()
    for row in rows:
        if _question_similarity(row.question, question) >= 0.85:
            return True
    return False


def _promote_positive_feedback(entry_id: str) -> None:
    entry = get_query_log_entry(entry_id)
    if entry.execution_status != "success":
        return
    if _has_similar_example(entry.data_source_id, entry.user_question):
        return
    create_example(
        entry.data_source_id,
        question=entry.user_question,
        sql=entry.generated_sql,
        notes="Auto-promoted from positive user feedback.",
        source="feedback",
    )


def submit_feedback(
    *,
    query_log_id: str,
    user_id: str,
    rating: FeedbackRating,
    comment: str | None = None,
) -> QueryFeedback:
    entry = get_query_log_entry(query_log_id)
    existing = QueryFeedbackRow.query.filter_by(
        query_log_id=query_log_id,
        user_id=user_id,
    ).first()
    if existing is not None:
        existing.rating = rating
        existing.comment = comment
        db.session.commit()
        feedback = _feedback_from_row(existing)
    else:
        row = QueryFeedbackRow(
            id=str(uuid.uuid4()),
            query_log_id=query_log_id,
            user_id=user_id,
            rating=rating,
            comment=comment,
            created_at=utc_now_iso(),
        )
        db.session.add(row)
        db.session.commit()
        feedback = _feedback_from_row(row)

    if rating == "up":
        _promote_positive_feedback(query_log_id)
    return feedback


def get_feedback_for_entry(query_log_id: str, *, user_id: str) -> QueryFeedback | None:
    row = QueryFeedbackRow.query.filter_by(
        query_log_id=query_log_id,
        user_id=user_id,
    ).first()
    if row is None:
        return None
    return _feedback_from_row(row)


def get_negative_feedback_context(
    data_source_id: str,
    question: str,
    *,
    limit: int = 3,
) -> list[dict[str, str]]:
    """Return similar past questions that received negative feedback."""
    feedback_rows = (
        QueryFeedbackRow.query.filter_by(rating="down")
        .order_by(QueryFeedbackRow.created_at.desc())
        .limit(100)
        .all()
    )
    if not feedback_rows:
        return []

    log_ids = [row.query_log_id for row in feedback_rows]
    logs = (
        QueryLogEntryRow.query.filter(
            QueryLogEntryRow.id.in_(log_ids),
            QueryLogEntryRow.data_source_id == data_source_id,
        )
        .all()
    )
    log_by_id = {row.id: row for row in logs}
    question_embedding = _embed(question)

    scored: list[tuple[float, QueryLogEntryRow, QueryFeedbackRow]] = []
    for feedback in feedback_rows:
        log = log_by_id.get(feedback.query_log_id)
        if log is None:
            continue
        score = _cosine(question_embedding, _embed(log.user_question))
        if score < 0.35:
            continue
        scored.append((score, log, feedback))

    scored.sort(key=lambda item: item[0], reverse=True)
    results: list[dict[str, str]] = []
    for _, log, feedback in scored[:limit]:
        results.append(
            {
                "question": log.user_question,
                "sql": log.generated_sql,
                "comment": feedback.comment or "",
            }
        )
    return results
