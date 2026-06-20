"""Tests for admin LLM settings endpoints."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text("ANTHROPIC_API_KEY=existing-key\n", encoding="utf-8")
    monkeypatch.setattr("app.services.env_settings_service.ENV_PATH", path)
    return path


def test_get_llm_settings(client, env_file, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    response = client.get("/api/admin/llm-settings")
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["provider"] == "anthropic"
    assert data["anthropic_api_key_set"] is True
    assert data["env_file_path"] == str(env_file)


def test_update_llm_settings_writes_env(client, env_file):
    response = client.put(
        "/api/admin/llm-settings",
        json={
            "provider": "ollama",
            "ollama_base_url": "http://127.0.0.1:11434",
            "ollama_model": "llama3.1",
        },
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["provider"] == "ollama"
    assert data["configured"] is True
    assert "LLM_PROVIDER=ollama" in env_file.read_text(encoding="utf-8")
    assert os.environ["LLM_PROVIDER"] == "ollama"


def test_update_preserves_existing_api_key_when_omitted(client, env_file):
    client.put(
        "/api/admin/llm-settings",
        json={
            "provider": "anthropic",
            "anthropic_model": "claude-sonnet-4-20250514",
        },
    )
    contents = env_file.read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY" in contents
    assert "existing-key" in contents


def test_update_replaces_api_key_when_provided(client, env_file):
    client.put(
        "/api/admin/llm-settings",
        json={
            "provider": "gemini",
            "gemini_api_key": "new-gemini-key",
            "gemini_model": "gemini-2.0-flash-lite",
        },
    )
    contents = env_file.read_text(encoding="utf-8")
    assert "GEMINI_API_KEY" in contents
    assert "new-gemini-key" in contents
    assert os.environ["GEMINI_API_KEY"] == "new-gemini-key"


def test_test_ollama_settings_reports_unreachable(client, env_file, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    response = client.post(
        "/api/admin/llm-settings/test",
        json={
            "provider": "ollama",
            "ollama_base_url": "http://127.0.0.1:59999",
            "ollama_model": "llama3.1",
        },
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["success"] is False
    assert "Cannot reach Ollama" in data["message"]
