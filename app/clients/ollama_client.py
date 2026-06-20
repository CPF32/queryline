"""Ollama client for structured tool-use calls against a local endpoint."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from app.models.chart_spec import ChartSpec
from app.schemas.chart_spec_generation import (
    CHART_SPEC_TOOL,
    CHART_SPEC_TOOL_NAME,
    parse_chart_spec_tool_output,
)
from app.schemas.sql_generation import SQL_GENERATION_TOOL, SqlGenerationToolOutput


def _anthropic_tool_to_ollama(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


class OllamaClient:
    """LLM client that talks to a local Ollama HTTP API."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._base_url = _normalize_base_url(
            base_url or os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        )
        self._model = model or os.environ.get("OLLAMA_MODEL", "qwen3-coder:30b")

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Ollama request failed ({exc.code}): {detail or exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Cannot reach Ollama at {self._base_url}. "
                "Install Ollama, run `ollama serve`, and pull a model "
                f"(`ollama pull {self._model}`)."
            ) from exc

    def _generate_tool_args(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tool: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._base_url:
            raise RuntimeError("OLLAMA_BASE_URL is not configured.")

        response = self._post_json(
            "/api/chat",
            {
                "model": self._model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "tools": [_anthropic_tool_to_ollama(tool)],
            },
        )
        message = response.get("message") or {}
        tool_calls = message.get("tool_calls") or []
        for call in tool_calls:
            function = call.get("function") or {}
            if function.get("name") != tool["name"]:
                continue
            arguments = function.get("arguments")
            if isinstance(arguments, str):
                return json.loads(arguments)
            if isinstance(arguments, dict):
                return arguments

        raise RuntimeError(
            f"Ollama did not return the expected tool call ({tool['name']}). "
            "Use a model with tool-calling support (e.g. llama3.1, qwen2.5)."
        )

    def generate_sql_tool_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> SqlGenerationToolOutput:
        raw = self._generate_tool_args(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tool=SQL_GENERATION_TOOL,
        )
        return SqlGenerationToolOutput.model_validate(raw)

    def generate_chart_spec_tool_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> ChartSpec:
        raw = self._generate_tool_args(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tool=CHART_SPEC_TOOL,
        )
        return parse_chart_spec_tool_output(raw)

    def test_connection(self) -> dict[str, Any]:
        """Ping Ollama and verify the configured model is available."""
        request = urllib.request.Request(
            f"{self._base_url}/api/tags",
            headers={"Content-Type": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Cannot reach Ollama at {self._base_url}. "
                "Install from https://ollama.com and run `ollama serve`."
            ) from exc

        models = [item.get("name", "") for item in payload.get("models", [])]
        normalized = {name.split(":", 1)[0] for name in models}
        model_base = self._model.split(":", 1)[0]
        if model_base not in normalized:
            raise RuntimeError(
                f"Model '{self._model}' is not available locally. "
                f"Run `ollama pull {self._model}`."
            )
        return {
            "success": True,
            "message": f"Connected to Ollama; model '{self._model}' is available.",
            "available_models": models,
        }
