"""Streaming SQL generation across configured LLM providers."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

from app.clients.claude_client import AnthropicClaudeClient
from app.clients.gemini_client import GeminiClient
from app.clients.llm_factory import get_llm_client
from app.clients.ollama_client import OllamaClient
from app.clients.openai_client import OpenAIClient
from app.clients.stream_helpers import ToolJsonAccumulator
from app.schemas.sql_generation import SQL_GENERATION_TOOL, SqlGenerationToolOutput


def _thinking_event(delta: str) -> dict[str, Any]:
    return {"type": "thinking", "delta": delta}


def _explanation_event(delta: str) -> dict[str, Any]:
    return {"type": "explanation_delta", "delta": delta}


def _complete_event(output: SqlGenerationToolOutput) -> dict[str, Any]:
    return {
        "type": "complete",
        "data": output.model_dump(mode="json"),
    }


def _extended_thinking_enabled() -> bool:
    return os.environ.get("ANTHROPIC_EXTENDED_THINKING", "true").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _stream_anthropic(
    client: AnthropicClaudeClient,
    *,
    system_prompt: str,
    user_prompt: str,
    enable_thinking: bool = True,
) -> Iterator[dict[str, Any]]:
    if not client._api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

    import anthropic

    anthropic_client = anthropic.Anthropic(api_key=client._api_key)
    stream_kwargs: dict[str, Any] = {
        "model": client._model,
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
        "tools": [SQL_GENERATION_TOOL],
        "tool_choice": {"type": "tool", "name": SQL_GENERATION_TOOL["name"]},
    }
    if enable_thinking and _extended_thinking_enabled():
        stream_kwargs["thinking"] = {"type": "enabled", "budget_tokens": 1024}

    try:
        with anthropic_client.messages.stream(**stream_kwargs) as stream:
            tool_json = ToolJsonAccumulator()
            for event in stream:
                if event.type != "content_block_delta":
                    continue
                delta = event.delta
                delta_type = getattr(delta, "type", None)
                if delta_type == "thinking_delta":
                    thinking = getattr(delta, "thinking", "")
                    if thinking:
                        yield _thinking_event(thinking)
                elif delta_type == "input_json_delta":
                    partial_json = getattr(delta, "partial_json", "")
                    explanation_delta = tool_json.add_delta(partial_json)
                    if explanation_delta:
                        yield _explanation_event(explanation_delta)

            final = stream.get_final_message()
            for block in final.content:
                if block.type == "tool_use" and block.name == SQL_GENERATION_TOOL["name"]:
                    output = SqlGenerationToolOutput.model_validate(block.input)
                    yield _complete_event(output)
                    return

            raise RuntimeError("Claude did not return the expected tool-use block.")
    except TypeError:
        if enable_thinking and _extended_thinking_enabled():
            yield from _stream_anthropic(
                client,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                enable_thinking=False,
            )
            return
        raise


def _ollama_tool_to_payload(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }


def _stream_ollama(
    client: OllamaClient,
    *,
    system_prompt: str,
    user_prompt: str,
) -> Iterator[dict[str, Any]]:
    if not client._base_url:
        raise RuntimeError("OLLAMA_BASE_URL is not configured.")

    payload = {
        "model": client._model,
        "stream": True,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "tools": [_ollama_tool_to_payload(SQL_GENERATION_TOOL)],
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{client._base_url}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            thinking_sent = ""
            tool_json = ToolJsonAccumulator()
            final_arguments: dict[str, Any] | None = None

            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                data = json.loads(line)
                message = data.get("message") or {}

                thinking = message.get("thinking") or ""
                if thinking and len(thinking) > len(thinking_sent):
                    yield _thinking_event(thinking[len(thinking_sent) :])
                    thinking_sent = thinking

                for call in message.get("tool_calls") or []:
                    function = call.get("function") or {}
                    if function.get("name") != SQL_GENERATION_TOOL["name"]:
                        continue
                    arguments = function.get("arguments")
                    if isinstance(arguments, str):
                        explanation_delta = tool_json.add_delta(arguments)
                        if explanation_delta:
                            yield _explanation_event(explanation_delta)
                    elif isinstance(arguments, dict):
                        final_arguments = arguments

                if data.get("done"):
                    if final_arguments is not None:
                        output = SqlGenerationToolOutput.model_validate(final_arguments)
                        yield _complete_event(output)
                        return
                    if tool_json.raw_json:
                        output = SqlGenerationToolOutput.model_validate(
                            tool_json.parse_complete()
                        )
                        yield _complete_event(output)
                        return

            if tool_json.raw_json:
                output = SqlGenerationToolOutput.model_validate(tool_json.parse_complete())
                yield _complete_event(output)
                return

            raise RuntimeError(
                f"Ollama did not return the expected tool call ({SQL_GENERATION_TOOL['name']})."
            )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Ollama request failed ({exc.code}): {detail or exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Cannot reach Ollama at {client._base_url}. "
            "Install Ollama, run `ollama serve`, and pull a model."
        ) from exc


def _stream_openai(
    client: OpenAIClient,
    *,
    system_prompt: str,
    user_prompt: str,
) -> Iterator[dict[str, Any]]:
    if not client._api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    from openai import OpenAI

    openai_client = OpenAI(api_key=client._api_key)
    tool_json = ToolJsonAccumulator()

    try:
        stream = openai_client.chat.completions.create(
            model=client._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=[_ollama_tool_to_payload(SQL_GENERATION_TOOL)],
            tool_choice={
                "type": "function",
                "function": {"name": SQL_GENERATION_TOOL["name"]},
            },
            stream=True,
        )

        for chunk in stream:
            for call in chunk.choices[0].delta.tool_calls or []:
                arguments = call.function.arguments if call.function else None
                if not arguments:
                    continue
                explanation_delta = tool_json.add_delta(arguments)
                if explanation_delta:
                    yield _explanation_event(explanation_delta)

        if tool_json.raw_json:
            output = SqlGenerationToolOutput.model_validate(tool_json.parse_complete())
            yield _complete_event(output)
            return

        raise RuntimeError(
            f"OpenAI did not return the expected function call ({SQL_GENERATION_TOOL['name']})."
        )
    except Exception as exc:
        if tool_json.raw_json:
            output = SqlGenerationToolOutput.model_validate(tool_json.parse_complete())
            yield _complete_event(output)
            return
        from app.clients.openai_client import _friendly_openai_error

        raise _friendly_openai_error(exc) from exc


def _stream_gemini(
    client: GeminiClient,
    *,
    system_prompt: str,
    user_prompt: str,
) -> Iterator[dict[str, Any]]:
    output = client.generate_sql_tool_output(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    if output.explanation:
        yield _explanation_event(output.explanation)
    yield _complete_event(output)


def stream_sql_generation(
    *,
    system_prompt: str,
    user_prompt: str,
    llm_client: Any | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield stream events: thinking, explanation_delta, complete."""
    client = llm_client or get_llm_client()
    if isinstance(client, AnthropicClaudeClient):
        yield from _stream_anthropic(
            client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        return
    if isinstance(client, OllamaClient):
        yield from _stream_ollama(
            client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        return
    if isinstance(client, OpenAIClient):
        yield from _stream_openai(
            client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        return
    if isinstance(client, GeminiClient):
        yield from _stream_gemini(
            client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        return

    output = client.generate_sql_tool_output(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    if output.explanation:
        yield _explanation_event(output.explanation)
    yield _complete_event(output)
