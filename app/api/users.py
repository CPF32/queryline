"""User management API endpoints (admin only)."""

from __future__ import annotations

from flask import Blueprint, request

from app.api.responses import list_response, success_response
from app.api.validation import parse_json
from app.auth.context import require_admin
from app.schemas.users import CreateUserRequest, UpdateUserRequest
from app.services import user_service

users_bp = Blueprint("users", __name__)


@users_bp.get("/users")
def list_users():
    require_admin()
    limit = request.args.get("limit", default=100, type=int)
    offset = request.args.get("offset", default=0, type=int)
    users, total = user_service.list_users(limit=limit, offset=offset)
    return list_response(
        [user.to_dict() for user in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@users_bp.post("/users")
def create_user():
    require_admin()
    body = parse_json(request, CreateUserRequest)
    user = user_service.create_user(
        username=body.username,
        domain=body.domain,
        display_name=body.display_name,
        is_admin=body.is_admin,
        is_developer=body.is_developer,
    )
    return success_response(user.to_dict(), status=201)


@users_bp.patch("/users/<user_id>")
def update_user(user_id: str):
    require_admin()
    body = parse_json(request, UpdateUserRequest)
    user = user_service.update_user(user_id, body.model_dump(exclude_unset=True))
    return success_response(user.to_dict())


@users_bp.delete("/users/<user_id>")
def delete_user(user_id: str):
    require_admin()
    user_service.delete_user(user_id)
    return "", 204
