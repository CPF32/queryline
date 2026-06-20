"""Profile update request schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    theme: Literal["light", "dark"] | None = None
