"""Request bodies for chat / query endpoints (CONTRACTS.md §5.8–§5.10)."""

from typing import Any

from pydantic import BaseModel, Field

from app.models.query_result import QueryColumnMeta


class ConversationMessage(BaseModel):
    role: str
    content: str


class GenerateSqlRequest(BaseModel):
    data_source_id: str
    session_id: str
    question: str = Field(min_length=1)
    conversation_id: str | None = None
    conversation_history: list[ConversationMessage] = Field(default_factory=list)
    retry_context: dict[str, Any] | None = None


class ExecuteQueryRequest(BaseModel):
    data_source_id: str
    session_id: str
    sql: str = Field(min_length=1)
    max_rows: int = Field(default=1000, ge=1, le=10_000)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    user_question: str = ""
    conversation_id: str | None = None


class GenerateAndExecuteRequest(BaseModel):
    data_source_id: str
    session_id: str
    question: str = Field(min_length=1)
    conversation_history: list[ConversationMessage] = Field(default_factory=list)
    max_rows: int = Field(default=1000, ge=1, le=10_000)
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class QueryResultPayload(BaseModel):
    columns: list[QueryColumnMeta]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    execution_ms: float


class ChartSpecRequest(BaseModel):
    data_source_id: str
    session_id: str
    user_question: str = Field(min_length=1)
    sql: str = Field(min_length=1)
    query_result: QueryResultPayload
    query_log_id: str | None = None
    chart_hint: str | None = None
    conversation_id: str | None = None
