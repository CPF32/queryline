"""Select the configured LLM client for SQL and chart generation."""

from __future__ import annotations

import os

from app.clients.claude_client import AnthropicClaudeClient, ClaudeClient
from app.clients.gemini_client import GeminiClient
from app.clients.ollama_client import OllamaClient
from app.clients.openai_client import OpenAIClient


def get_llm_client() -> ClaudeClient:
    """Return the active LLM client based on ``LLM_PROVIDER``."""
    provider = os.environ.get("LLM_PROVIDER", "anthropic").strip().lower()
    if provider == "gemini":
        return GeminiClient()
    if provider == "openai":
        return OpenAIClient()
    if provider == "anthropic":
        return AnthropicClaudeClient()
    if provider == "ollama":
        return OllamaClient()
    raise RuntimeError(
        f"Unsupported LLM_PROVIDER '{provider}'. "
        "Use 'anthropic', 'gemini', 'openai', or 'ollama'."
    )


def llm_configured() -> bool:
    """True when the selected provider has enough configuration to call the LLM."""
    provider = os.environ.get("LLM_PROVIDER", "anthropic").strip().lower()
    if provider == "gemini":
        return bool(os.environ.get("GEMINI_API_KEY"))
    if provider == "openai":
        return bool(os.environ.get("OPENAI_API_KEY"))
    if provider == "ollama":
        return bool(os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip())
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def llm_api_key_configured() -> bool:
    """Backward-compatible alias for ``llm_configured``."""
    return llm_configured()
