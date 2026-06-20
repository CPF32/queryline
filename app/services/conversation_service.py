"""Persistent chat conversation storage."""

from __future__ import annotations

import uuid
from typing import Any

from app.db import ConversationMessageRow, ConversationRow, db
from app.errors import NotFoundError, ValidationAppError
from app.models.conversation import Conversation, ConversationMessage
from app.util.time import utc_now_iso


def _conversation_from_row(row: ConversationRow) -> Conversation:
    return Conversation(
        id=row.id,
        user_id=row.user_id,
        data_source_id=row.data_source_id,
        title=row.title,
        created_at=row.created_at,
        updated_at=row.updated_at,
        archived_at=row.archived_at,
    )


def _message_from_row(row: ConversationMessageRow) -> ConversationMessage:
    return ConversationMessage(
        id=row.id,
        conversation_id=row.conversation_id,
        role=row.role,
        content=row.content,
        sequence=row.sequence,
        created_at=row.created_at,
        payload=row.payload,
    )


def _get_conversation_row(conversation_id: str, *, user_id: str) -> ConversationRow:
    row = db.session.get(ConversationRow, conversation_id)
    if row is None or row.user_id != user_id:
        raise NotFoundError(f"Conversation {conversation_id} not found.")
    return row


def _next_sequence(conversation_id: str) -> int:
    latest = (
        ConversationMessageRow.query.filter_by(conversation_id=conversation_id)
        .order_by(ConversationMessageRow.sequence.desc())
        .first()
    )
    return (latest.sequence + 1) if latest else 0


def _title_from_question(question: str) -> str:
    cleaned = " ".join(question.split())
    if len(cleaned) <= 60:
        return cleaned or "New chat"
    return f"{cleaned[:57]}..."


def list_conversations(
    *,
    user_id: str,
    data_source_id: str | None = None,
    archived: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Conversation], int]:
    query = ConversationRow.query.filter_by(user_id=user_id)
    if data_source_id:
        query = query.filter_by(data_source_id=data_source_id)
    if archived:
        query = query.filter(ConversationRow.archived_at.isnot(None))
    else:
        query = query.filter(ConversationRow.archived_at.is_(None))
    total = query.count()
    rows = (
        query.order_by(ConversationRow.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_conversation_from_row(row) for row in rows], total


def create_conversation(
    *,
    user_id: str,
    data_source_id: str,
    title: str | None = None,
) -> Conversation:
    now = utc_now_iso()
    row = ConversationRow(
        id=str(uuid.uuid4()),
        user_id=user_id,
        data_source_id=data_source_id,
        title=title or "New chat",
        created_at=now,
        updated_at=now,
    )
    db.session.add(row)
    db.session.commit()
    return _conversation_from_row(row)


def get_conversation(conversation_id: str, *, user_id: str) -> Conversation:
    return _conversation_from_row(_get_conversation_row(conversation_id, user_id=user_id))


def update_conversation(
    conversation_id: str,
    *,
    user_id: str,
    title: str | None = None,
    archived: bool | None = None,
) -> Conversation:
    row = _get_conversation_row(conversation_id, user_id=user_id)
    if title is not None:
        cleaned = title.strip()
        if not cleaned:
            raise ValidationAppError("Conversation title cannot be empty.")
        row.title = cleaned
    if archived is not None:
        row.archived_at = utc_now_iso() if archived else None
    row.updated_at = utc_now_iso()
    db.session.commit()
    return _conversation_from_row(row)


def delete_conversation(conversation_id: str, *, user_id: str) -> None:
    row = _get_conversation_row(conversation_id, user_id=user_id)
    ConversationMessageRow.query.filter_by(conversation_id=conversation_id).delete()
    db.session.delete(row)
    db.session.commit()


def list_messages(conversation_id: str, *, user_id: str) -> list[ConversationMessage]:
    _get_conversation_row(conversation_id, user_id=user_id)
    rows = (
        ConversationMessageRow.query.filter_by(conversation_id=conversation_id)
        .order_by(ConversationMessageRow.sequence.asc())
        .all()
    )
    return [_message_from_row(row) for row in rows]


def append_message(
    conversation_id: str,
    *,
    user_id: str,
    role: str,
    content: str,
    payload: dict[str, Any] | None = None,
) -> ConversationMessage:
    row = _get_conversation_row(conversation_id, user_id=user_id)
    message = ConversationMessageRow(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role=role,
        content=content,
        sequence=_next_sequence(conversation_id),
        payload=payload,
        created_at=utc_now_iso(),
    )
    row.updated_at = message.created_at
    if role == "user" and row.title == "New chat":
        row.title = _title_from_question(content)
    db.session.add(message)
    db.session.commit()
    return _message_from_row(message)
