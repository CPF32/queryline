"""Query log entry model for audit and history.

See CONTRACTS.md §4.7.
"""

from typing import Any, Self

from pydantic import BaseModel


class QueryLogEntry(BaseModel):
    """Record of a user question, generated SQL, and execution outcome."""

    id: str
    data_source_id: str
    session_id: str
    user_question: str
    generated_sql: str
    execution_status: str
    error_message: str | None = None
    row_count: int | None = None
    execution_ms: float | None = None
    chart_spec: dict[str, Any] | None = None
    created_at: str
    user_id: str | None = None
    workspace_id: str | None = None

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)
