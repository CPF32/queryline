"""First-run setup state and machine owner identity."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.auth.identity import _system_domain, _system_username
from app.errors import ValidationAppError
from app.paths import get_app_data_dir, is_desktop_runtime

SETUP_FILENAME = "setup.json"


def _setup_path() -> Path:
    return get_app_data_dir() / SETUP_FILENAME


def _read_state() -> dict[str, Any]:
    path = _setup_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_state(state: dict[str, Any]) -> None:
    path = _setup_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _resolve_owner_from_env() -> tuple[str | None, str | None]:
    username = os.environ.get("OWNER_USERNAME", "").strip() or None
    domain_raw = os.environ.get("OWNER_DOMAIN", "").strip()
    domain = domain_raw or None
    if username:
        return username, domain

    admin_users = os.environ.get("AUTH_ADMIN_USERS", "").strip()
    if admin_users:
        first = admin_users.split(",")[0].strip()
        if first:
            if "\\" in first:
                domain_part, user_part = first.split("\\", 1)
                return user_part.strip() or None, domain_part.strip() or None
            if "@" in first:
                user_part, domain_part = first.split("@", 1)
                return user_part.strip() or None, domain_part.strip() or None
            return first, None

    return _system_username(), _system_domain()


def ensure_bootstrapped() -> dict[str, Any]:
    """Create setup.json with the machine owner on first launch."""
    state = _read_state()
    if state.get("owner_username"):
        return state

    owner_username, owner_domain = _resolve_owner_from_env()
    state = {
        "complete": False,
        "owner_username": owner_username,
        "owner_domain": owner_domain,
        "ollama_self_host": None,
    }
    _write_state(state)
    return state


def get_setup_status() -> dict[str, Any]:
    state = ensure_bootstrapped()
    wizard_required = _requires_setup_wizard()
    complete = bool(state.get("complete")) or not wizard_required
    return {
        "complete": complete,
        "wizard_required": wizard_required,
        "ollama_self_host": state.get("ollama_self_host"),
        "owner_username": state.get("owner_username"),
        "owner_domain": state.get("owner_domain"),
        "is_desktop": is_desktop_runtime(),
        "platform": os.name,
        "default_ollama_base_url": os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
    }


def _requires_setup_wizard() -> bool:
    if os.environ.get("AUTH_MODE", "system").strip().lower() == "disabled":
        return False
    if is_desktop_runtime():
        return True
    return bool(os.environ.get("APP_DATA_DIR"))


def is_setup_complete() -> bool:
    return bool(_read_state().get("complete"))


def _identity_matches(
    *,
    username: str,
    domain: str | None,
    owner_username: str | None,
    owner_domain: str | None,
) -> bool:
    if not owner_username:
        return False
    if username.lower() != owner_username.lower():
        return False
    if not owner_domain or not domain:
        return True
    return domain.lower() == owner_domain.lower()


def is_owner_identity(*, username: str, domain: str | None) -> bool:
    state = ensure_bootstrapped()
    return _identity_matches(
        username=username,
        domain=domain,
        owner_username=state.get("owner_username"),
        owner_domain=state.get("owner_domain"),
    )


def is_owner_user(*, username: str, domain: str | None) -> bool:
    return is_owner_identity(username=username, domain=domain)


def complete_setup(*, ollama_self_host: bool) -> dict[str, Any]:
    state = ensure_bootstrapped()
    if state.get("complete"):
        raise ValidationAppError("Setup has already been completed.")

    state["complete"] = True
    state["ollama_self_host"] = ollama_self_host
    _write_state(state)
    return get_setup_status()


def recommend_ollama_model(*, total_ram_gb: float) -> dict[str, str]:
    """Recommend an Ollama model based on available system memory."""
    if total_ram_gb >= 32:
        return {
            "model": "qwen3-coder:30b",
            "label": "Qwen3 Coder 30B",
            "reason": "Your system has enough memory for the largest recommended coding model.",
        }
    if total_ram_gb >= 16:
        return {
            "model": "qwen2.5-coder:14b",
            "label": "Qwen2.5 Coder 14B",
            "reason": "Balanced coding model for systems with 16 GB or more RAM.",
        }
    if total_ram_gb >= 8:
        return {
            "model": "qwen2.5-coder:7b",
            "label": "Qwen2.5 Coder 7B",
            "reason": "Lightweight coding model suited to 8 GB systems.",
        }
    return {
        "model": "llama3.2:3b",
        "label": "Llama 3.2 3B",
        "reason": "Compact model for systems with limited memory.",
    }
