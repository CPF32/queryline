"""Persistent chat conversation endpoints."""

from __future__ import annotations

from flask import Blueprint, request

from app.api.responses import list_response, success_response
from app.api.validation import parse_json
from app.auth.context import require_user
from app.schemas.conversations import (
    AppendMessageRequest,
    CreateConversationRequest,
    UpdateConversationRequest,
)
from app.services import conversation_service

conversations_bp = Blueprint("conversations", __name__)


@conversations_bp.get("/conversations")
def list_conversations():
    user = require_user()
    data_source_id = request.args.get("data_source_id")
    archived = request.args.get("archived", default="false").lower() == "true"
    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)
    conversations, total = conversation_service.list_conversations(
        user_id=user.id,
        data_source_id=data_source_id,
        archived=archived,
        limit=limit,
        offset=offset,
    )
    return list_response(
        [conversation.to_dict() for conversation in conversations],
        total=total,
        limit=limit,
        offset=offset,
    )


@conversations_bp.post("/conversations")
def create_conversation():
    user = require_user()
    body = parse_json(request, CreateConversationRequest)
    conversation = conversation_service.create_conversation(
        user_id=user.id,
        data_source_id=body.data_source_id,
        title=body.title,
    )
    return success_response(conversation.to_dict(), status=201)


@conversations_bp.get("/conversations/<conversation_id>")
def get_conversation(conversation_id: str):
    user = require_user()
    conversation = conversation_service.get_conversation(conversation_id, user_id=user.id)
    return success_response(conversation.to_dict())


@conversations_bp.patch("/conversations/<conversation_id>")
def update_conversation(conversation_id: str):
    user = require_user()
    body = parse_json(request, UpdateConversationRequest)
    conversation = conversation_service.update_conversation(
        conversation_id,
        user_id=user.id,
        title=body.title,
        archived=body.archived,
    )
    return success_response(conversation.to_dict())


@conversations_bp.delete("/conversations/<conversation_id>")
def delete_conversation(conversation_id: str):
    user = require_user()
    conversation_service.delete_conversation(conversation_id, user_id=user.id)
    return "", 204


@conversations_bp.get("/conversations/<conversation_id>/messages")
def list_messages(conversation_id: str):
    user = require_user()
    messages = conversation_service.list_messages(conversation_id, user_id=user.id)
    return success_response([message.to_dict() for message in messages])


@conversations_bp.post("/conversations/<conversation_id>/messages")
def append_message(conversation_id: str):
    user = require_user()
    body = parse_json(request, AppendMessageRequest)
    message = conversation_service.append_message(
        conversation_id,
        user_id=user.id,
        role=body.role,
        content=body.content,
        payload=body.payload,
    )
    return success_response(message.to_dict(), status=201)
