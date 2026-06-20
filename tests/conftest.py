"""Pytest fixtures shared across test modules."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


@pytest.fixture()
def sample_sqlite_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "analytics.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, region TEXT)")
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL)")
    conn.execute(
        "CREATE VIEW customer_regions AS "
        "SELECT id, name, region FROM customers"
    )
    conn.execute(
        "INSERT INTO customers (id, name, region) VALUES (1, 'Acme', 'North'), (2, 'Beta', 'South')"
    )
    conn.execute("INSERT INTO orders (id, customer_id, amount) VALUES (1, 1, 100.0), (2, 2, 50.0)")
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from app import create_app
    from app.db import db

    monkeypatch.setenv("AUTH_MODE", "disabled")
    metadata_db = tmp_path / "admin_metadata.db"
    flask_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{metadata_db}",
        }
    )
    with flask_app.app_context():
        db.create_all()
    yield flask_app
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
