"""Authentication API endpoints."""

from __future__ import annotations

from flask import Blueprint, request

from app.api.responses import success_response
from app.api.validation import parse_json
from app.auth.context import (
    DEV_USER_HEADER,
    REMOTE_USER_HEADER,
    SYSTEM_USER_HEADER,
    clear_session_user,
    get_current_user,
    is_admin_username,
    require_user,
    set_session_user,
)
from app.auth.credentials import (
    credential_login_enabled,
    normalize_login_identity,
    verify_credentials,
)
from app.auth.identity import resolve_identity
from app.errors import UnauthorizedError, ValidationAppError
from app.schemas.auth import LoginRequest
from app.schemas.profile import UpdateProfileRequest
from app.services import setup_service, user_service

auth_bp = Blueprint("auth", __name__)


def _resolved_system_identity():
    from app.auth.context import _auth_mode

    return resolve_identity(
        auth_mode=_auth_mode(),
        remote_user_header=request.headers.get(REMOTE_USER_HEADER),
        system_user_header=request.headers.get(SYSTEM_USER_HEADER),
        dev_user_header=request.headers.get(DEV_USER_HEADER),
    )


@auth_bp.get("/auth/system-identity")
def system_identity():
    """Return the OS or SSO username hint for pre-filling the sign-in form."""
    identity = _resolved_system_identity()
    if identity is None:
        return success_response(None)
    return success_response(
        {
            "username": identity.username,
            "domain": identity.domain,
            "display_name": identity.display_name,
        }
    )


@auth_bp.get("/auth/me")
def get_me():
    user = get_current_user()
    if user is None:
        user = require_user()
    return success_response(user.to_dict())


@auth_bp.post("/auth/login")
def login():
    if not credential_login_enabled():
        raise ValidationAppError(
            "Username and password sign-in is not configured for this deployment."
        )

    body = parse_json(request, LoginRequest)
    try:
        identity = normalize_login_identity(body.username, body.domain)
    except ValueError as exc:
        raise ValidationAppError(str(exc)) from exc

    if not verify_credentials(
        username=identity.username,
        password=body.password,
        domain=identity.domain,
    ):
        raise UnauthorizedError("Invalid username or password.")

    user = user_service.get_or_create_user(
        username=identity.username,
        domain=identity.domain,
        display_name=identity.display_name,
        is_admin=is_admin_username(
            username=identity.username,
            domain=identity.domain,
            display_name=identity.display_name,
        )
        or setup_service.is_owner_identity(
            username=identity.username,
            domain=identity.domain,
        ),
    )
    set_session_user(user.id)
    return success_response(user.to_dict())


@auth_bp.post("/auth/logout")
def logout():
    clear_session_user()
    return success_response({"signed_out": True})


@auth_bp.patch("/auth/me")
def update_me():
    user = require_user()
    body = parse_json(request, UpdateProfileRequest)
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise ValidationAppError("No profile changes provided.")
    updated = user_service.update_user(user.id, data)
    return success_response(updated.to_dict())
