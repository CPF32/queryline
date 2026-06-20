"""Tests for streaming tool JSON helpers."""

from __future__ import annotations

from app.clients.stream_helpers import ToolJsonAccumulator, decode_json_string_fragment


def test_decode_json_string_fragment_handles_escapes() -> None:
    assert decode_json_string_fragment("Hello\\nworld") == "Hello\nworld"


def test_tool_json_accumulator_streams_explanation_deltas() -> None:
    accumulator = ToolJsonAccumulator()
    first = accumulator.add_delta('{"sql": "SELECT 1", "explanation": "Hello')
    second = accumulator.add_delta(' world", "tables_used": []}')
    assert first == "Hello"
    assert second == " world"
    assert accumulator.parse_complete() == {
        "sql": "SELECT 1",
        "explanation": "Hello world",
        "tables_used": [],
    }
