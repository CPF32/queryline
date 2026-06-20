"""Tests for first-run setup and machine owner protection."""

from __future__ import annotations

import json

import pytest


@pytest.fixture()
def setup_app(tmp_path, monkeypatch):
    from app import create_app
    from app.db import db

    data_dir = tmp_path / "appdata"
    data_dir.mkdir()
    monkeypatch.setenv("APP_DATA_DIR", str(data_dir))
    monkeypatch.setenv("OWNER_USERNAME", "machineowner")
    monkeypatch.setenv("AUTH_MODE", "system")
    monkeypatch.setenv("AUTH_ADMIN_USERS", "")

    metadata_db = tmp_path / "admin.db"
    flask_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{metadata_db}",
        }
    )
    with flask_app.app_context():
        db.create_all()
    yield flask_app, data_dir
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


def test_setup_status_bootstraps_owner(setup_app):
    app, data_dir = setup_app
    client = app.test_client()

    response = client.get("/api/v1/setup/status")
    assert response.status_code == 200
    body = response.get_json()["data"]
    assert body["wizard_required"] is True
    assert body["complete"] is False
    assert body["owner_username"] == "machineowner"

    setup_file = data_dir / "setup.json"
    assert setup_file.is_file()
    saved = json.loads(setup_file.read_text())
    assert saved["owner_username"] == "machineowner"


def test_complete_setup_marks_complete(setup_app):
    app, _data_dir = setup_app
    client = app.test_client()

    complete = client.post(
        "/api/v1/setup/complete",
        json={"ollama_self_host": False},
    )
    assert complete.status_code == 200
    assert complete.get_json()["data"]["complete"] is True

    status = client.get("/api/v1/setup/status")
    assert status.get_json()["data"]["complete"] is True


def test_owner_cannot_be_demoted(setup_app, monkeypatch):
    app, _data_dir = setup_app
    monkeypatch.setattr(
        "app.auth.credentials.verify_local_system_password",
        lambda **kwargs: kwargs["password"] == "secret",
    )
    client = app.test_client()

    client.post("/api/v1/setup/complete", json={"ollama_self_host": False})
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "machineowner", "password": "secret"},
    )
    assert login.status_code == 200
    user = login.get_json()["data"]
    assert user["is_admin"] is True
    assert user["is_owner"] is True

    demote = client.patch(
        f"/api/v1/users/{user['id']}",
        json={"is_admin": False},
    )
    assert demote.status_code == 422
    assert "owner" in demote.get_json()["error"]["message"].lower()


def test_owner_cannot_be_deleted(setup_app, monkeypatch):
    app, _data_dir = setup_app
    monkeypatch.setattr(
        "app.auth.credentials.verify_local_system_password",
        lambda **kwargs: kwargs["password"] == "secret",
    )
    client = app.test_client()

    client.post("/api/v1/setup/complete", json={"ollama_self_host": False})
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "machineowner", "password": "secret"},
    )
    user_id = login.get_json()["data"]["id"]

    deleted = client.delete(f"/api/v1/users/{user_id}")
    assert deleted.status_code == 422
