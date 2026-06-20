"""Authenticated application user."""

from typing import Literal, Self

from pydantic import BaseModel

ThemePreference = Literal["light", "dark"]


class User(BaseModel):
    id: str
    username: str
    domain: str | None = None
    display_name: str
    is_admin: bool = False
    is_owner: bool = False
    theme: ThemePreference = "dark"
    created_at: str
    last_seen_at: str

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)
