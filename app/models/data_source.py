"""DataSource domain model.

See CONTRACTS.md §4.1.
"""

from typing import Any, Self

from pydantic import BaseModel, Field


class DataSource(BaseModel):
    """A configured database connection available for chat queries."""

    id: str
    name: str
    connector_type: str
    connection_config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    dialect_name: str
    created_at: str
    updated_at: str
    user_id: str | None = None
    workspace_id: str | None = None

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)
