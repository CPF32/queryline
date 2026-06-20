"""Few-shot SQL example model for LLM prompt context.

See CONTRACTS.md §4.6.
"""

from typing import Self

from pydantic import BaseModel


class SqlExample(BaseModel):
    """Natural-language question paired with reference SQL."""

    id: str
    data_source_id: str
    question: str
    sql: str
    notes: str | None = None
    created_at: str
    updated_at: str
    user_id: str | None = None
    workspace_id: str | None = None

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)
