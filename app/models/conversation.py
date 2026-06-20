"""Persistent chat conversation models."""

from __future__ import annotations

from typing import Any, Self

from pydantic import BaseModel


class Conversation(BaseModel):
    id: str
    user_id: str
    data_source_id: str
    title: str
    created_at: str
    updated_at: str
    archived_at: str | None = None

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)


class ConversationMessage(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sequence: int
    created_at: str
    payload: dict[str, Any] | None = None

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)
