"""Resolve application data paths for desktop and development runtimes."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_SLUG = "text-to-sql-analytics"


def is_desktop_runtime() -> bool:
    return os.environ.get("DESKTOP_RUNTIME") == "1" or bool(os.environ.get("APP_DATA_DIR"))


def get_app_data_dir() -> Path:
    override = os.environ.get("APP_DATA_DIR")
    if override:
        path = Path(override)
    elif is_desktop_runtime():
        if sys.platform == "darwin":
            path = Path.home() / "Library" / "Application Support" / APP_SLUG
        elif sys.platform == "win32":
            local = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
            path = Path(local) / APP_SLUG
        else:
            xdg = os.environ.get("XDG_DATA_HOME")
            base = Path(xdg) if xdg else Path.home() / ".local" / "share"
            path = base / APP_SLUG
    else:
        path = Path(__file__).resolve().parent.parent
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_env_file_path() -> Path:
    if is_desktop_runtime():
        return get_app_data_dir() / ".env"
    return Path(__file__).resolve().parent.parent / ".env"


def get_default_database_url() -> str:
    if is_desktop_runtime():
        db_path = get_app_data_dir() / "text_to_sql_admin.db"
        return f"sqlite:///{db_path.as_posix()}"
    return "sqlite:///text_to_sql_admin.db"


def ensure_fernet_key() -> str:
    """Load or create a stable Fernet key for encrypting stored secrets."""
    existing = os.environ.get("FERNET_KEY", "").strip()
    if existing:
        return existing

    env_path = get_env_file_path()
    if env_path.is_file():
        try:
            from dotenv import dotenv_values

            file_value = (dotenv_values(env_path).get("FERNET_KEY") or "").strip()
            if file_value:
                os.environ["FERNET_KEY"] = file_value
                return file_value
        except ImportError:
            pass

    from cryptography.fernet import Fernet
    from dotenv import set_key

    key = Fernet.generate_key().decode("utf-8")
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if not env_path.is_file():
        env_path.touch()
    set_key(env_path, "FERNET_KEY", key, quote_mode="auto")
    os.environ["FERNET_KEY"] = key
    return key
