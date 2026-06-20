"""OpenAI client for structured function-call output."""

from __future__ import annotations

import json
import os
from typing import Any

from app.models.chart_spec import ChartSpec
from app.schemas.chart_spec_generation import (
    CHART_SPEC_TOOL,
    parse_chart_spec_tool_output,
)
from app.schemas.sql_generation import SQL_GENERATION_TOOL, SqlGenerationToolOutput


def _anthropic_tool_to_openai(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }


def _friendly_openai_error(exc: Exception) -> RuntimeError:
    message = str(exc)
    lowered = message.lower()
    if "401" in message or "invalid api key" in lowered or "incorrect api key" in lowered:
        return RuntimeError(
            "OpenAI API key was rejected. Check OPENAI_API_KEY in your .env file."
        )
    if "429" in message or "rate limit" in lowered:
        return RuntimeError(
            "OpenAI rate limit exceeded. Wait a moment and retry, or choose a smaller model."
        )
    if "404" in message and "model" in lowered:
        return RuntimeError(
            "OpenAI model not found or unavailable. "
            "Try OPENAI_MODEL=gpt-4o-mini in .env."
        )
    return RuntimeError(message)


class OpenAIClient:
    """Production OpenAI client using the Chat Completions API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def _generate_function_args(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tool: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)
        try:
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                tools=[_anthropic_tool_to_openai(tool)],
                tool_choice={
                    "type": "function",
                    "function": {"name": tool["name"]},
                },
            )
        except Exception as exc:
            raise _friendly_openai_error(exc) from exc

        message = response.choices[0].message
        for call in message.tool_calls or []:
            if call.function.name == tool["name"]:
                raw = call.function.arguments
                if isinstance(raw, dict):
                    return raw
                return json.loads(raw or "{}")

        raise RuntimeError(
            f"OpenAI did not return the expected function call ({tool['name']})."
        )

    def generate_sql_tool_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> SqlGenerationToolOutput:
        raw = self._generate_function_args(
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
        raw = self._generate_function_args(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tool=CHART_SPEC_TOOL,
        )
        return parse_chart_spec_tool_output(raw)
