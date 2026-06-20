"""Setup wizard request schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CompleteSetupRequest(BaseModel):
    ollama_self_host: bool
    provider: Literal["anthropic", "gemini", "ollama"] | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = Field(default=None, min_length=1)
