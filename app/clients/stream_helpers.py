"""Helpers for streaming partial tool-call JSON from LLM providers."""

from __future__ import annotations

import codecs
import json
import re
from typing import Any

_EXPLANATION_PATTERN = re.compile(
    r'"explanation"\s*:\s*"((?:[^"\\]|\\.)*)(?:"|$)'
)


def decode_json_string_fragment(fragment: str) -> str:
    """Decode a partial JSON string value (handles incomplete trailing escapes)."""
    try:
        return json.loads(f'"{fragment}"')
    except json.JSONDecodeError:
        if "\\" in fragment:
            try:
                return codecs.decode(fragment, "unicode_escape")
            except UnicodeDecodeError:
                pass
        return fragment


class ToolJsonAccumulator:
    """Accumulates streamed tool JSON and extracts explanation text deltas."""

    def __init__(self) -> None:
        self._json = ""
        self._last_explanation = ""

    @property
    def raw_json(self) -> str:
        return self._json

    def add_delta(self, delta: str) -> str | None:
        if not delta:
            return None
        self._json += delta
        match = _EXPLANATION_PATTERN.search(self._json)
        if not match:
            return None
        partial = decode_json_string_fragment(match.group(1))
        if partial == self._last_explanation:
            return None
        new_part = partial[len(self._last_explanation) :]
        self._last_explanation = partial
        return new_part if new_part else None

    def parse_complete(self) -> dict[str, Any]:
        return json.loads(self._json)
