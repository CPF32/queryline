"""Admin endpoints for LLM provider configuration."""

from __future__ import annotations

import os
import time

from flask import Blueprint, request

from app.api.responses import success_response
from app.api.validation import parse_json
from app.clients.claude_client import AnthropicClaudeClient
from app.clients.gemini_client import GeminiClient
from app.clients.ollama_client import OllamaClient
from app.clients.openai_client import OpenAIClient
from app.schemas.llm_settings import TestLlmSettingsRequest, UpdateLlmSettingsRequest
from app.services.env_settings_service import get_llm_settings, save_llm_settings

admin_llm_settings_bp = Blueprint("admin_llm_settings", __name__)


@admin_llm_settings_bp.get("/llm-settings")
def read_llm_settings():
    return success_response(get_llm_settings())


@admin_llm_settings_bp.put("/llm-settings")
def update_llm_settings():
    body = parse_json(request, UpdateLlmSettingsRequest)
    payload = request.get_json(silent=True) or {}
    settings = save_llm_settings(
        provider=body.provider,
        anthropic_api_key=body.anthropic_api_key,
        anthropic_model=body.anthropic_model,
        gemini_api_key=body.gemini_api_key,
        gemini_model=body.gemini_model,
        openai_api_key=body.openai_api_key,
        openai_model=body.openai_model,
        ollama_base_url=body.ollama_base_url,
        ollama_model=body.ollama_model,
        update_anthropic_api_key="anthropic_api_key" in payload,
        update_gemini_api_key="gemini_api_key" in payload,
        update_openai_api_key="openai_api_key" in payload,
    )
    return success_response(settings)


@admin_llm_settings_bp.post("/llm-settings/test")
def test_llm_settings():
    body = parse_json(request, TestLlmSettingsRequest)
    current = get_llm_settings()
    provider = body.provider or current["provider"]

    started = time.perf_counter()
    try:
        if provider == "ollama":
            base_url = body.ollama_base_url or current["ollama_base_url"]
            model = body.ollama_model or current["ollama_model"]
            result = OllamaClient(base_url=base_url, model=model).test_connection()
        elif provider == "gemini":
            api_key = body.gemini_api_key
            if not api_key and not current["gemini_api_key_set"]:
                raise RuntimeError("GEMINI_API_KEY is not configured.")
            if not api_key:
                api_key = os.environ.get("GEMINI_API_KEY", "")
            model = body.gemini_model or current["gemini_model"]
            client = GeminiClient(api_key=api_key, model=model)
            client.generate_sql_tool_output(
                system_prompt="You generate SQL using the submit_sql tool.",
                user_prompt="Return a trivial SELECT 1 query.",
            )
            result = {
                "success": True,
                "message": f"Gemini model '{model}' responded successfully.",
            }
        elif provider == "openai":
            api_key = body.openai_api_key
            if not api_key and not current["openai_api_key_set"]:
                raise RuntimeError("OPENAI_API_KEY is not configured.")
            if not api_key:
                api_key = os.environ.get("OPENAI_API_KEY", "")
            model = body.openai_model or current["openai_model"]
            client = OpenAIClient(api_key=api_key, model=model)
            client.generate_sql_tool_output(
                system_prompt="You generate SQL using the submit_sql tool.",
                user_prompt="Return a trivial SELECT 1 query.",
            )
            result = {
                "success": True,
                "message": f"OpenAI model '{model}' responded successfully.",
            }
        else:
            api_key = body.anthropic_api_key
            if not api_key and not current["anthropic_api_key_set"]:
                raise RuntimeError("ANTHROPIC_API_KEY is not configured.")
            if not api_key:
                api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            model = body.anthropic_model or current["anthropic_model"]
            client = AnthropicClaudeClient(api_key=api_key, model=model)
            client.generate_sql_tool_output(
                system_prompt="You generate SQL using the submit_sql tool.",
                user_prompt="Return a trivial SELECT 1 query.",
            )
            result = {
                "success": True,
                "message": f"Anthropic model '{model}' responded successfully.",
            }
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return success_response(
            {
                "success": False,
                "message": str(exc),
                "latency_ms": latency_ms,
            }
        )

    latency_ms = int((time.perf_counter() - started) * 1000)
    return success_response(
        {
            "success": result["success"],
            "message": result["message"],
            "latency_ms": latency_ms,
        }
    )
