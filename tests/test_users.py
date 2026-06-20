"""Tests for user management API."""

from __future__ import annotations


def test_users_crud_requires_admin(client, monkeypatch, sample_sqlite_db):
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
    blocked = test_client.get("/api/v1/users")
    assert blocked.status_code == 401

    test_client.post("/api/v1/auth/logout", json={})
    test_client.post(
        "/api/v1/auth/login",
        json={"username": "adminuser", "password": "secret"},
    )

    created = test_client.post(
        "/api/v1/users",
        json={
            "username": "newuser",
            "domain": "CORP",
            "display_name": "New User",
            "is_admin": False,
        },
    )
    assert created.status_code == 201
    user_id = created.get_json()["data"]["id"]

    listed = test_client.get("/api/v1/users")
    assert listed.status_code == 200
    usernames = {entry["username"] for entry in listed.get_json()["data"]}
    assert "newuser" in usernames

    updated = test_client.patch(
        f"/api/v1/users/{user_id}",
        json={"is_admin": True},
    )
    assert updated.status_code == 200
    assert updated.get_json()["data"]["is_admin"] is True

    deleted = test_client.delete(f"/api/v1/users/{user_id}")
    assert deleted.status_code == 204
