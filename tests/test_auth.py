"""Tests for authentication and access control."""

from __future__ import annotations

import uuid


def test_auth_me_disabled_mode(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["username"] == "anonymous"
    assert body["data"]["is_admin"] is True


def test_update_profile(client):
    me = client.get("/api/v1/auth/me")
    user_id = me.get_json()["data"]["id"]

    updated = client.patch(
        "/api/v1/auth/me",
        json={"display_name": "Custom Name"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["data"]["display_name"] == "Custom Name"

    again = client.get("/api/v1/auth/me")
    assert again.get_json()["data"]["display_name"] == "Custom Name"
    assert again.get_json()["data"]["id"] == user_id


def test_system_auth_requires_login_session(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "system")
    from app import create_app
    from app.db import db

    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
    test_client = app.test_client()

    blocked = test_client.get(
        "/api/v1/auth/me",
        headers={"X-System-User": "CORP\\jdoe"},
    )
    assert blocked.status_code == 401


def test_system_auth_login_with_os_password(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "system")
    monkeypatch.setattr(
        "app.auth.credentials.verify_local_system_password",
        lambda **kwargs: kwargs["password"] == "correct",
    )
    from app import create_app
    from app.db import db

    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
    test_client = app.test_client()

    login_response = test_client.post(
        "/api/v1/auth/login",
        json={"username": "jdoe", "password": "correct", "domain": "CORP"},
    )
    assert login_response.status_code == 200
    user = login_response.get_json()["data"]
    assert user["username"] == "jdoe"
    assert user["domain"] == "CORP"

    me = test_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.get_json()["data"]["username"] == "jdoe"


def test_admin_write_requires_admin(client, monkeypatch, sample_sqlite_db):
    monkeypatch.setenv("AUTH_MODE", "system")
    monkeypatch.setenv("AUTH_ADMIN_USERS", "adminuser")
    monkeypatch.setattr(
        "app.auth.credentials.verify_local_system_password",
        lambda **kwargs: kwargs["password"] == "secret",
    )
    from app import create_app
    from app.db import db

    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
    test_client = app.test_client()

    test_client.post(
        "/api/v1/auth/login",
        json={"username": "regularuser", "password": "secret"},
    )

    response = test_client.post(
        "/api/v1/data-sources",
        json={
            "name": "blocked",
            "connector_type": "sqlite",
            "connection_config": {"file_path": str(sample_sqlite_db)},
            "is_active": True,
        },
    )
    assert response.status_code == 401

    test_client.post("/api/v1/auth/logout", json={})
    test_client.post(
        "/api/v1/auth/login",
        json={"username": "adminuser", "password": "secret"},
    )

    allowed = test_client.post(
        "/api/v1/data-sources",
        json={
            "name": f"allowed-{uuid.uuid4().hex[:8]}",
            "connector_type": "sqlite",
            "connection_config": {"file_path": str(sample_sqlite_db)},
            "is_active": True,
        },
    )
    assert allowed.status_code == 201


def test_login_and_logout_with_dev_password(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "disabled")
    monkeypatch.setenv("AUTH_DEV_PASSWORD", "secret")

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "jdoe", "password": "secret", "domain": "CORP"},
    )
    assert login_response.status_code == 200
    user = login_response.get_json()["data"]
    assert user["username"] == "jdoe"
    assert user["domain"] == "CORP"

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.get_json()["data"]["username"] == "jdoe"

    logout = client.post("/api/v1/auth/logout", json={})
    assert logout.status_code == 200

    blocked = client.get("/api/v1/auth/me")
    assert blocked.status_code == 200
    assert blocked.get_json()["data"]["username"] == "anonymous"


def test_login_rejects_invalid_password(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "disabled")
    monkeypatch.setenv("AUTH_DEV_PASSWORD", "secret")

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "jdoe", "password": "wrong"},
    )
    assert response.status_code == 401


def test_system_identity_returns_sso_hint(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "system")
    from app import create_app
    from app.db import db

    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
    test_client = app.test_client()

    response = test_client.get(
        "/api/v1/auth/system-identity",
        headers={"X-System-User": "CORP\\jdoe"},
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["username"] == "jdoe"
    assert data["domain"] == "CORP"
    assert data["display_name"] == "CORP\\jdoe"
