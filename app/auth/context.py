"""Flask request authentication context."""

from __future__ import annotations

import os

from flask import Flask, g, request, session

from app.auth.credentials import uses_local_system_password
from app.auth.identity import resolve_identity
from app.errors import UnauthorizedError
from app.models.user import User
from app.services import user_service
from app.services import setup_service

AUTH_MODE_ENV = "AUTH_MODE"
REMOTE_USER_HEADER = "X-Remote-User"
SYSTEM_USER_HEADER = "X-System-User"
DEV_USER_HEADER = "X-Dev-User"
ADMIN_USERS_ENV = "AUTH_ADMIN_USERS"
SESSION_USER_ID_KEY = "auth.user_id"


def _auth_mode() -> str:
    return os.environ.get(AUTH_MODE_ENV, "system").strip().lower()


def _admin_usernames() -> set[str]:
    raw = os.environ.get(ADMIN_USERS_ENV, "")
    names: set[str] = set()
    for entry in raw.split(","):
        value = entry.strip()
        if not value:
            continue
        domain, username = value, None
        if "\\" in value:
            domain, username = value.split("\\", 1)
            names.add(username.strip().lower())
            names.add(f"{domain.strip()}\\{username.strip()}".lower())
        else:
            names.add(value.lower())
    return names


def init_auth(app: Flask) -> None:
    """Register before_request hook that resolves the current user."""

    @app.before_request
    def _attach_current_user() -> None:
        user_id = session.get(SESSION_USER_ID_KEY)
        if user_id:
            user = user_service.get_user(user_id)
            if user is not None:
                g.current_user = user
                return
            clear_session_user()

        if uses_local_system_password():
            g.current_user = None
            return

        identity = resolve_identity(
            auth_mode=_auth_mode(),
            remote_user_header=request.headers.get(REMOTE_USER_HEADER),
            system_user_header=request.headers.get(SYSTEM_USER_HEADER),
            dev_user_header=request.headers.get(DEV_USER_HEADER),
        )
        if identity is None:
            g.current_user = None
            return
        g.current_user = user_service.get_or_create_user(
            username=identity.username,
            domain=identity.domain,
            display_name=identity.display_name,
            is_admin=_is_admin_identity(identity)
            or setup_service.is_owner_identity(
                username=identity.username,
                domain=identity.domain,
            ),
        )


def is_admin_username(*, username: str, domain: str | None, display_name: str) -> bool:
    admins = _admin_usernames()
    if not admins:
        return False
    candidates = {
        username.lower(),
        display_name.lower(),
    }
    if domain:
        candidates.add(f"{domain}\\{username}".lower())
        candidates.add(f"{username}@{domain}".lower())
    return bool(candidates & admins)


def _is_admin_identity(identity) -> bool:
    return is_admin_username(
        username=identity.username,
        domain=identity.domain,
        display_name=identity.display_name,
    )


def set_session_user(user_id: str) -> None:
    session[SESSION_USER_ID_KEY] = user_id
    session.permanent = True


def clear_session_user() -> None:
    session.pop(SESSION_USER_ID_KEY, None)


def get_current_user() -> User | None:
    return getattr(g, "current_user", None)


def require_user() -> User:
    user = get_current_user()
    if user is None:
        if _auth_mode() == "disabled":
            return user_service.get_or_create_user(
                username="anonymous",
                domain=None,
                display_name="Anonymous",
                is_admin=True,
            )
        raise UnauthorizedError("Authentication required.")
    return user


def require_admin() -> User:
    user = require_user()
    if not user.is_admin:
        raise UnauthorizedError("Administrator access required.")
    return user


def require_developer() -> User:
    user = require_admin()
    if not user.is_developer:
        raise UnauthorizedError("Developer access required.")
    return user
