"""Glossary term model for business vocabulary injected into LLM prompts.

See CONTRACTS.md §4.5.
"""

from typing import Self

from pydantic import BaseModel


class GlossaryTerm(BaseModel):
    """Business term definition scoped to a data source."""

    id: str
    data_source_id: str
    term: str
    definition: str
    sql_expression: str | None = None
    table_id: str | None = None
    column_id: str | None = None
    created_at: str
    updated_at: str
    user_id: str | None = None
    workspace_id: str | None = None

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)
