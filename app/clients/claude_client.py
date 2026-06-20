"""Anthropic Claude client for structured tool-use calls."""

from __future__ import annotations

import json
import os
from typing import Any, Protocol

from app.models.chart_spec import ChartSpec
from app.schemas.chart_spec_generation import (
    CHART_SPEC_TOOL,
    CHART_SPEC_TOOL_NAME,
    parse_chart_spec_tool_output,
)
from app.schemas.sql_generation import SQL_GENERATION_TOOL, SqlGenerationToolOutput


class ClaudeClient(Protocol):
    """Interface for Claude message calls (mockable in tests)."""

    def generate_sql_tool_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> SqlGenerationToolOutput:
        """Call Claude with tool-use and return parsed structured output."""
        ...

    def generate_chart_spec_tool_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> ChartSpec:
        """Call Claude with tool-use and return parsed ChartSpec output."""
        ...


class AnthropicClaudeClient:
    """Production Claude client using the Anthropic Messages API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    def generate_sql_tool_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> SqlGenerationToolOutput:
        if not self._api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)
        response = client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[SQL_GENERATION_TOOL],
            tool_choice={"type": "tool", "name": SQL_GENERATION_TOOL["name"]},
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == SQL_GENERATION_TOOL["name"]:
                return SqlGenerationToolOutput.model_validate(block.input)

        raise RuntimeError("Claude did not return the expected tool-use block.")

    def generate_chart_spec_tool_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> ChartSpec:
        if not self._api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)
        response = client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[CHART_SPEC_TOOL],
            tool_choice={"type": "tool", "name": CHART_SPEC_TOOL_NAME},
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == CHART_SPEC_TOOL_NAME:
                return parse_chart_spec_tool_output(block.input)

        raise RuntimeError("Claude did not return the expected chart-spec tool-use block.")


def parse_tool_output(raw: dict[str, Any]) -> SqlGenerationToolOutput:
    """Parse a tool input dict into a validated output model."""
    return SqlGenerationToolOutput.model_validate(raw)


def tool_output_to_json(output: SqlGenerationToolOutput) -> str:
    return json.dumps(output.model_dump(mode="json"))
