"""Text-to-SQL analytics Flask application package."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from flask import Flask, send_from_directory
from pydantic import ValidationError

from app.api.admin import (
    admin_data_sources_bp,
    admin_examples_bp,
    admin_glossary_bp,
    admin_llm_settings_bp,
    admin_query_log_bp,
    admin_schema_bp,
)
from app.api.auth import auth_bp
from app.api.setup import setup_bp
from app.api.chat import chat_bp
from app.api.conversations import conversations_bp
from app.api.feedback import feedback_bp
from app.api.users import users_bp
from app.api.responses import error_response
from app.auth.context import init_auth, require_admin, require_user
from app.db import init_db
from app.errors import AppError
from app.paths import get_default_database_url


def _get_dist_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "dist"
    return Path(__file__).resolve().parent.parent / "dist"


DIST_DIR = _get_dist_dir()

_ADMIN_RESOURCE_MARKERS = (
    "/schema",
    "/glossary",
    "/examples",
    "/llm-settings",
    "/query-log",
    "/connectors",
    "/users",
)


def _is_admin_read_path(path: str) -> bool:
    return any(marker in path for marker in _ADMIN_RESOURCE_MARKERS)


def _is_admin_write_path(path: str) -> bool:
    if _is_admin_read_path(path):
        return True
    if "/data-sources" in path:
        return True
    return False


def _register_api_blueprints(app: Flask, prefix: str, *, name_suffix: str = "") -> None:
    suffix = f"_{name_suffix}" if name_suffix else ""
    app.register_blueprint(
        admin_data_sources_bp,
        url_prefix=prefix,
        name=f"admin_data_sources{suffix}",
    )
    app.register_blueprint(
        admin_schema_bp,
        url_prefix=prefix,
        name=f"admin_schema{suffix}",
    )
    app.register_blueprint(
        admin_glossary_bp,
        url_prefix=prefix,
        name=f"admin_glossary{suffix}",
    )
    app.register_blueprint(
        admin_examples_bp,
        url_prefix=prefix,
        name=f"admin_examples{suffix}",
    )
    app.register_blueprint(
        admin_query_log_bp,
        url_prefix=prefix,
        name=f"admin_query_log{suffix}",
    )
    app.register_blueprint(
        admin_llm_settings_bp,
        url_prefix=prefix,
        name=f"admin_llm_settings{suffix}",
    )
    app.register_blueprint(chat_bp, url_prefix=prefix, name=f"chat{suffix}")
    app.register_blueprint(auth_bp, url_prefix=prefix, name=f"auth{suffix}")
    app.register_blueprint(
        conversations_bp,
        url_prefix=prefix,
        name=f"conversations{suffix}",
    )
    app.register_blueprint(feedback_bp, url_prefix=prefix, name=f"feedback{suffix}")
    app.register_blueprint(users_bp, url_prefix=prefix, name=f"users{suffix}")
    app.register_blueprint(setup_bp, url_prefix=prefix, name=f"setup{suffix}")


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.update(
        {
            "SQLALCHEMY_DATABASE_URI": os.environ.get(
                "DATABASE_URL", get_default_database_url()
            ),
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "TESTING": False,
            "SECRET_KEY": os.environ.get(
                "SECRET_KEY",
                os.environ.get("FERNET_KEY", "dev-only-change-me"),
            ),
            "SESSION_COOKIE_HTTPONLY": True,
            "SESSION_COOKIE_SAMESITE": "Lax",
        }
    )
    if config:
        app.config.update(config)

    init_db(app)
    init_auth(app)

    from app.services import setup_service

    setup_service.ensure_bootstrapped()

    @app.before_request
    def _enforce_api_access():
        from flask import request as flask_request

        path = flask_request.path
        method = flask_request.method

        if not path.startswith("/api/"):
            return
        if path == "/health" or path.endswith("/auth/me"):
            return
        if path.endswith("/auth/login") or path.endswith("/auth/logout"):
            return
        if path.endswith("/auth/system-identity"):
            return
        if "/setup/" in path:
            return

        user = require_user()

        if path.startswith("/api/admin"):
            require_admin()
            return

        if _is_admin_read_path(path):
            require_admin()
            return

        if method not in ("GET", "HEAD", "OPTIONS") and _is_admin_write_path(path):
            require_admin()

    _register_api_blueprints(app, "/api/v1")
    _register_api_blueprints(app, "/api/admin", name_suffix="admin")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    if DIST_DIR.is_dir():

        @app.route("/", defaults={"path": ""})
        @app.route("/<path:path>")
        def serve_frontend(path: str):
            if path.startswith("api/"):
                return error_response("not_found", "Resource not found.", status=404, details=None)
            target = DIST_DIR / path
            if path and target.is_file():
                return send_from_directory(DIST_DIR, path)
            return send_from_directory(DIST_DIR, "index.html")

    @app.errorhandler(AppError)
    def handle_app_error(exc: AppError):
        return error_response(
            exc.code,
            exc.message,
            status=exc.status_code,
            details=exc.details,
        )

    @app.errorhandler(ValidationError)
    def handle_validation_error(exc: ValidationError):
        return error_response(
            "validation_error",
            "Request validation failed.",
            status=422,
            details=exc.errors(),
        )

    @app.errorhandler(404)
    def handle_not_found(_exc):
        return error_response("not_found", "Resource not found.", status=404, details=None)

    @app.errorhandler(500)
    def handle_internal_error(_exc):
        return error_response(
            "internal_error",
            "An unexpected error occurred.",
            status=500,
            details=None,
        )

    return app
