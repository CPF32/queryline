"""Read and write LLM-related settings in the project ``.env`` file."""

from __future__ import annotations

import os
from typing import Any, Literal

from dotenv import dotenv_values, set_key

from app.paths import get_env_file_path

LlmProvider = Literal["anthropic", "gemini", "openai", "ollama"]

ENV_PATH = get_env_file_path()

LLM_ENV_KEYS = (
    "LLM_PROVIDER",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
)

DEFAULTS: dict[str, str] = {
    "LLM_PROVIDER": "anthropic",
    "ANTHROPIC_MODEL": "claude-sonnet-4-20250514",
    "GEMINI_MODEL": "gemini-2.0-flash-lite",
    "OPENAI_MODEL": "gpt-4o-mini",
    "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
    "OLLAMA_MODEL": "qwen3-coder:30b",
}


def _read_env_file() -> dict[str, str | None]:
    if not ENV_PATH.is_file():
        return {}
    return dotenv_values(ENV_PATH)


def _effective_value(key: str, file_values: dict[str, str | None]) -> str:
    if key in os.environ and os.environ[key]:
        return os.environ[key]
    file_value = file_values.get(key)
    if file_value:
        return file_value
    return DEFAULTS.get(key, "")


def get_llm_settings() -> dict[str, Any]:
    """Return current LLM settings for the admin UI (API keys are not exposed)."""
    file_values = _read_env_file()
    provider = _effective_value("LLM_PROVIDER", file_values).strip().lower() or "anthropic"
    anthropic_key = _effective_value("ANTHROPIC_API_KEY", file_values)
    gemini_key = _effective_value("GEMINI_API_KEY", file_values)
    openai_key = _effective_value("OPENAI_API_KEY", file_values)
    ollama_base_url = _effective_value("OLLAMA_BASE_URL", file_values)

    return {
        "provider": provider,
        "anthropic_model": _effective_value("ANTHROPIC_MODEL", file_values),
        "gemini_model": _effective_value("GEMINI_MODEL", file_values),
        "openai_model": _effective_value("OPENAI_MODEL", file_values),
        "ollama_base_url": ollama_base_url,
        "ollama_model": _effective_value("OLLAMA_MODEL", file_values),
        "anthropic_api_key_set": bool(anthropic_key),
        "gemini_api_key_set": bool(gemini_key),
        "openai_api_key_set": bool(openai_key),
        "configured": _provider_configured(
            provider,
            anthropic_key=anthropic_key,
            gemini_key=gemini_key,
            openai_key=openai_key,
            ollama_base_url=ollama_base_url,
        ),
        "env_file_path": str(ENV_PATH),
    }


def _provider_configured(
    provider: str,
    *,
    anthropic_key: str,
    gemini_key: str,
    openai_key: str,
    ollama_base_url: str,
) -> bool:
    if provider == "gemini":
        return bool(gemini_key)
    if provider == "openai":
        return bool(openai_key)
    if provider == "ollama":
        return bool(ollama_base_url.strip())
    return bool(anthropic_key)


def save_llm_settings(
    *,
    provider: LlmProvider,
    anthropic_api_key: str | None = None,
    anthropic_model: str | None = None,
    gemini_api_key: str | None = None,
    gemini_model: str | None = None,
    openai_api_key: str | None = None,
    openai_model: str | None = None,
    ollama_base_url: str | None = None,
    ollama_model: str | None = None,
    update_anthropic_api_key: bool = False,
    update_gemini_api_key: bool = False,
    update_openai_api_key: bool = False,
) -> dict[str, Any]:
    """Persist settings to ``.env`` and apply them to the running process."""
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not ENV_PATH.is_file():
        ENV_PATH.touch()

    file_values = _read_env_file()
    updates: dict[str, str] = {"LLM_PROVIDER": provider}

    if anthropic_model is not None:
        updates["ANTHROPIC_MODEL"] = anthropic_model
    if gemini_model is not None:
        updates["GEMINI_MODEL"] = gemini_model
    if openai_model is not None:
        updates["OPENAI_MODEL"] = openai_model
    if ollama_base_url is not None:
        updates["OLLAMA_BASE_URL"] = ollama_base_url.strip()
    if ollama_model is not None:
        updates["OLLAMA_MODEL"] = ollama_model.strip()

    if update_anthropic_api_key:
        updates["ANTHROPIC_API_KEY"] = anthropic_api_key or ""
    elif anthropic_api_key is None:
        existing = _effective_value("ANTHROPIC_API_KEY", file_values)
        if existing:
            updates["ANTHROPIC_API_KEY"] = existing

    if update_gemini_api_key:
        updates["GEMINI_API_KEY"] = gemini_api_key or ""
    elif gemini_api_key is None:
        existing = _effective_value("GEMINI_API_KEY", file_values)
        if existing:
            updates["GEMINI_API_KEY"] = existing

    if update_openai_api_key:
        updates["OPENAI_API_KEY"] = openai_api_key or ""
    elif openai_api_key is None:
        existing = _effective_value("OPENAI_API_KEY", file_values)
        if existing:
            updates["OPENAI_API_KEY"] = existing

    for key, value in updates.items():
        set_key(ENV_PATH, key, value, quote_mode="auto")
        os.environ[key] = value

    return get_llm_settings()
