"""User persistence and lookup."""

from __future__ import annotations

import uuid

from app.db import UserRow, db
from app.errors import NotFoundError, ValidationAppError
from app.models.user import User
from app.services import setup_service
from app.util.time import utc_now_iso


def _user_from_row(row: UserRow) -> User:
    is_owner = setup_service.is_owner_user(username=row.username, domain=row.domain)
    return User(
        id=row.id,
        username=row.username,
        domain=row.domain,
        display_name=row.display_name,
        is_admin=row.is_admin or is_owner,
        is_owner=is_owner,
        theme=row.theme if row.theme in ("light", "dark") else "dark",
        created_at=row.created_at,
        last_seen_at=row.last_seen_at,
    )


def _find_user_row(*, username: str, domain: str | None) -> UserRow | None:
    query = UserRow.query.filter_by(username=username)
    if domain:
        query = query.filter_by(domain=domain)
    else:
        query = query.filter(UserRow.domain.is_(None))
    return query.first()


def get_or_create_user(
    *,
    username: str,
    domain: str | None,
    display_name: str,
    is_admin: bool,
) -> User:
    row = _find_user_row(username=username, domain=domain)
    now = utc_now_iso()
    if row is None:
        row = UserRow(
            id=str(uuid.uuid4()),
            username=username,
            domain=domain,
            display_name=display_name,
            is_admin=is_admin,
            created_at=now,
            last_seen_at=now,
        )
        db.session.add(row)
    else:
        row.last_seen_at = now
        if is_admin:
            row.is_admin = True
    db.session.commit()
    return _user_from_row(row)


def get_user(user_id: str) -> User | None:
    row = db.session.get(UserRow, user_id)
    if row is None:
        return None
    return _user_from_row(row)


def list_users(*, limit: int = 100, offset: int = 0) -> tuple[list[User], int]:
    query = UserRow.query
    total = query.count()
    rows = (
        query.order_by(UserRow.display_name.asc(), UserRow.username.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_user_from_row(row) for row in rows], total


def create_user(
    *,
    username: str,
    domain: str | None,
    display_name: str,
    is_admin: bool = False,
) -> User:
    cleaned_username = username.strip()
    cleaned_display = display_name.strip()
    if not cleaned_username or not cleaned_display:
        raise ValidationAppError("Username and display name are required.")
    if _find_user_row(username=cleaned_username, domain=domain):
        raise ValidationAppError("A user with this username already exists.")
    now = utc_now_iso()
    row = UserRow(
        id=str(uuid.uuid4()),
        username=cleaned_username,
        domain=domain.strip() if domain else None,
        display_name=cleaned_display,
        is_admin=is_admin,
        created_at=now,
        last_seen_at=now,
    )
    db.session.add(row)
    db.session.commit()
    return _user_from_row(row)


def update_user(user_id: str, data: dict[str, object]) -> User:
    row = db.session.get(UserRow, user_id)
    if row is None:
        raise NotFoundError(f"User {user_id} not found.")

    if "username" in data:
        cleaned_username = str(data["username"]).strip()
        if not cleaned_username:
            raise ValidationAppError("Username cannot be empty.")
        next_domain = row.domain
        if "domain" in data:
            domain_value = data["domain"]
            next_domain = str(domain_value).strip() if domain_value else None
        existing = _find_user_row(username=cleaned_username, domain=next_domain)
        if existing is not None and existing.id != user_id:
            raise ValidationAppError("A user with this username already exists.")
        row.username = cleaned_username

    if "domain" in data and "username" not in data:
        domain_value = data["domain"]
        next_domain = str(domain_value).strip() if domain_value else None
        existing = _find_user_row(username=row.username, domain=next_domain)
        if existing is not None and existing.id != user_id:
            raise ValidationAppError("A user with this username already exists.")
        row.domain = next_domain
    elif "domain" in data:
        domain_value = data["domain"]
        row.domain = str(domain_value).strip() if domain_value else None

    if "display_name" in data:
        cleaned = str(data["display_name"]).strip()
        if not cleaned:
            raise ValidationAppError("Display name cannot be empty.")
        row.display_name = cleaned

    if "is_admin" in data:
        next_admin = bool(data["is_admin"])
        if setup_service.is_owner_user(username=row.username, domain=row.domain) and not next_admin:
            raise ValidationAppError(
                "The machine owner account cannot be demoted to a regular user."
            )
        row.is_admin = next_admin

    if "theme" in data:
        theme = str(data["theme"])
        if theme not in ("light", "dark"):
            raise ValidationAppError("Theme must be 'light' or 'dark'.")
        row.theme = theme

    row.last_seen_at = utc_now_iso()
    db.session.commit()
    return _user_from_row(row)


def delete_user(user_id: str) -> None:
    row = db.session.get(UserRow, user_id)
    if row is None:
        raise NotFoundError(f"User {user_id} not found.")
    if setup_service.is_owner_user(username=row.username, domain=row.domain):
        raise ValidationAppError("The machine owner account cannot be deleted.")
    db.session.delete(row)
    db.session.commit()
