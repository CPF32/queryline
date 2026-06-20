"""Request/response models for admin LLM settings."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

LlmProviderName = Literal["anthropic", "gemini", "openai", "ollama"]


class UpdateLlmSettingsRequest(BaseModel):
    provider: LlmProviderName
    anthropic_api_key: str | None = None
    anthropic_model: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = None


class TestLlmSettingsRequest(BaseModel):
    provider: LlmProviderName | None = None
    anthropic_api_key: str | None = None
    anthropic_model: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = None


class LlmSettingsResponse(BaseModel):
    provider: LlmProviderName
    anthropic_model: str
    gemini_model: str
    openai_model: str
    ollama_base_url: str
    ollama_model: str
    anthropic_api_key_set: bool
    gemini_api_key_set: bool
    openai_api_key_set: bool
    configured: bool
    env_file_path: str

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class LlmTestResult(BaseModel):
    success: bool
    message: str
    latency_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
