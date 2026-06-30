"""Diagnostic log request schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class CreateDiagnosticEventRequest(BaseModel):
    level: Literal["error", "warning", "info"] = "error"
    source: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=4000)
    details: dict[str, Any] | None = None
