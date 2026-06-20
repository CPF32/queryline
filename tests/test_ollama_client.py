"""Unit tests for the Ollama client."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.clients.ollama_client import OllamaClient


def test_generate_sql_tool_output_parses_tool_call() -> None:
    client = OllamaClient(base_url="http://localhost:11434", model="llama3.1")
    response_payload = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "submit_sql",
                        "arguments": {
                            "sql": "SELECT 1",
                            "explanation": "Returns one row.",
                            "tables_used": [],
                            "chart_hint": "table_only",
                            "confidence": "high",
                        },
                    }
                }
            ],
        }
    }

    with patch("urllib.request.urlopen") as urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_payload).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        urlopen.return_value = mock_response

        result = client.generate_sql_tool_output(
            system_prompt="system",
            user_prompt="user",
        )

    assert result.sql == "SELECT 1"
    assert result.explanation == "Returns one row."


def test_test_connection_requires_model() -> None:
    client = OllamaClient(base_url="http://localhost:11434", model="llama3.1")
    tags_payload = {"models": [{"name": "mistral:latest"}]}

    with patch("urllib.request.urlopen") as urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(tags_payload).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        urlopen.return_value = mock_response

        with pytest.raises(RuntimeError, match="llama3.1"):
            client.test_connection()
