"""User management request schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    domain: str | None = Field(default=None, max_length=255)
    display_name: str = Field(min_length=1, max_length=255)
    is_admin: bool = False
    is_developer: bool = False


class UpdateUserRequest(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=255)
    domain: str | None = Field(default=None, max_length=255)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    is_admin: bool | None = None
    is_developer: bool | None = None
    theme: Literal["light", "dark"] | None = None
