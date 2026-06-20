"""Adapter-level query result model (not persisted).

See CONTRACTS.md §3.2.
"""

from typing import Any, Self

from pydantic import BaseModel


class QueryColumnMeta(BaseModel):
    name: str
    type: str

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)


class QueryResult(BaseModel):
    columns: list[QueryColumnMeta]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    execution_ms: float

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)
