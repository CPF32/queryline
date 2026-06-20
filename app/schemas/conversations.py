"""Conversation history request schemas."""

from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    data_source_id: str
    title: str | None = None


class UpdateConversationRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    archived: bool | None = None


class AppendMessageRequest(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1)
    payload: dict | None = None
