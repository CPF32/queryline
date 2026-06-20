"""Google Gemini client for structured function-call output."""

from __future__ import annotations

import os
import re
import time
from typing import Any

from app.models.chart_spec import ChartSpec
from app.schemas.chart_spec_generation import (
    CHART_SPEC_TOOL,
    parse_chart_spec_tool_output,
)
from app.schemas.sql_generation import (
    SQL_GENERATION_TOOL,
    SqlGenerationToolOutput,
)


def _anthropic_tool_to_function_declaration(tool: dict[str, Any]):
    from google.genai import types

    return types.FunctionDeclaration(
        name=tool["name"],
        description=tool["description"],
        parameters=tool["input_schema"],
    )


def _friendly_gemini_error(exc: Exception) -> RuntimeError:
    message = str(exc)
    lowered = message.lower()
    if "429" in message or "resource_exhausted" in lowered or "quota" in lowered:
        retry_hint = ""
        match = re.search(r"retry in ([0-9.]+)s", lowered)
        if match:
            retry_hint = f" Retry in about {int(float(match.group(1)))} seconds."
        return RuntimeError(
            "Gemini API quota exceeded for this model/key."
            f"{retry_hint} Try GEMINI_MODEL=gemini-2.0-flash-lite, enable billing "
            "in Google AI Studio, or switch LLM_PROVIDER=anthropic."
        )
    if "401" in message or "403" in message or "invalid api key" in lowered:
        return RuntimeError(
            "Gemini API key was rejected. Check GEMINI_API_KEY in your .env file."
        )
    if "404" in message and "model" in lowered:
        return RuntimeError(
            "Gemini model not found or unavailable. "
            "Try GEMINI_MODEL=gemini-2.0-flash-lite in .env."
        )
    return RuntimeError(message)


class GeminiClient:
    """Production Gemini client using the Google Gen AI SDK."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._model = model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-lite")

    def _generate_function_args(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tool: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")

        from google import genai
        from google.genai import types

        declaration = _anthropic_tool_to_function_declaration(tool)
        client = genai.Client(api_key=self._api_key)
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[types.Tool(function_declarations=[declaration])],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode="ANY",
                    allowed_function_names=[tool["name"]],
                )
            ),
        )

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=self._model,
                    contents=user_prompt,
                    config=config,
                )
                parts = response.candidates[0].content.parts
                for part in parts:
                    if part.function_call and part.function_call.name == tool["name"]:
                        args = part.function_call.args
                        if isinstance(args, dict):
                            return args
                        return dict(args)

                raise RuntimeError(
                    f"Gemini did not return the expected function call ({tool['name']})."
                )
            except Exception as exc:
                last_error = exc
                message = str(exc).lower()
                if attempt == 0 and (
                    "429" in str(exc)
                    or "resource_exhausted" in message
                    or "quota" in message
                ):
                    delay = 45
                    match = re.search(r"retry in ([0-9.]+)s", message)
                    if match:
                        delay = min(int(float(match.group(1))) + 1, 60)
                    time.sleep(delay)
                    continue
                raise _friendly_gemini_error(exc) from exc

        assert last_error is not None
        raise _friendly_gemini_error(last_error) from last_error

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
