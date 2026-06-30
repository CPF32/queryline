"""Tests for developer diagnostic logs."""

from __future__ import annotations


def _login(test_client, username: str) -> None:
    test_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "secret"},
    )


def test_diagnostic_logs_require_developer(client, monkeypatch, sample_sqlite_db):
    monkeypatch.setenv("AUTH_MODE", "system")
    monkeypatch.setenv("AUTH_ADMIN_USERS", "adminuser,devuser")
    monkeypatch.setattr(
        "app.auth.credentials.verify_local_system_password",
        lambda **kwargs: kwargs["password"] == "secret",
    )
    from app import create_app
    from app.db import UserRow, db
    from app.services import diagnostic_log_service, user_service

    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        dev = user_service.create_user(
            username="devuser",
            domain=None,
            display_name="Dev User",
            is_admin=True,
            is_developer=True,
        )
        diagnostic_log_service.log_event(
            level="error",
            source="test",
            message="boom",
            details={"step": "one"},
            user_id=dev.id,
        )
    test_client = app.test_client()

    _login(test_client, "regularuser")
    blocked = test_client.get("/api/v1/diagnostic-logs")
    assert blocked.status_code == 401

    test_client.post("/api/v1/auth/logout", json={})
    _login(test_client, "adminuser")
    admin_blocked = test_client.get("/api/v1/diagnostic-logs")
    assert admin_blocked.status_code == 401

    test_client.post("/api/v1/auth/logout", json={})
    _login(test_client, "devuser")
    listed = test_client.get("/api/v1/diagnostic-logs")
    assert listed.status_code == 200
    payload = listed.get_json()
    assert payload["meta"]["total"] == 1
    assert payload["data"][0]["message"] == "boom"
    assert payload["data"][0]["source"] == "test"

    cleared = test_client.delete("/api/v1/diagnostic-logs")
    assert cleared.status_code == 200
    assert cleared.get_json()["data"]["deleted"] == 1


def test_owner_has_developer_access(client, monkeypatch, sample_sqlite_db):
    monkeypatch.setenv("AUTH_MODE", "system")
    monkeypatch.setenv("AUTH_ADMIN_USERS", "owneruser")
    monkeypatch.setattr(
        "app.auth.credentials.verify_local_system_password",
        lambda **kwargs: kwargs["password"] == "secret",
    )
    monkeypatch.setattr(
        "app.services.setup_service.is_owner_user",
        lambda **kwargs: kwargs["username"] == "owneruser",
    )
    from app import create_app
    from app.db import db

    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
    test_client = app.test_client()

    _login(test_client, "owneruser")
    me = test_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    profile = me.get_json()["data"]
    assert profile["is_owner"] is True
    assert profile["is_developer"] is True

    logs = test_client.get("/api/v1/diagnostic-logs")
    assert logs.status_code == 200


def test_client_diagnostic_event_is_stored(client, monkeypatch, sample_sqlite_db):
    monkeypatch.setenv("AUTH_MODE", "system")
    monkeypatch.setenv("AUTH_ADMIN_USERS", "devuser")
    monkeypatch.setattr(
        "app.auth.credentials.verify_local_system_password",
        lambda **kwargs: kwargs["password"] == "secret",
    )
    from app import create_app
    from app.db import db
    from app.services import user_service

    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        user_service.create_user(
            username="devuser",
            domain=None,
            display_name="Dev User",
            is_admin=True,
            is_developer=True,
        )
    test_client = app.test_client()

    _login(test_client, "devuser")
    posted = test_client.post(
        "/api/v1/diagnostic-events",
        json={
            "level": "error",
            "source": "chat",
            "message": "client failure",
            "details": {"kind": "network"},
        },
    )
    assert posted.status_code == 204

    listed = test_client.get("/api/v1/diagnostic-logs")
    entries = listed.get_json()["data"]
    assert any(entry["source"] == "client:chat" for entry in entries)
