"""Types for the text-to-SQL generation service."""

from typing import Any, Literal, Self

from pydantic import BaseModel, Field


ConfidenceLevel = Literal["high", "medium", "low"]


class SqlGenerationResult(BaseModel):
    """Outcome of a single SQL generation attempt."""

    success: bool
    sql: str | None = None
    explanation: str
    tables_used: list[str] = Field(default_factory=list)
    matched_glossary_terms: list[str] = Field(default_factory=list)
    chart_hint: str | None = None
    confidence: ConfidenceLevel | None = None
    attempt_number: int = 1
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)


class SqlGenerationToolOutput(BaseModel):
    """Structured output from Claude tool-use."""

    sql: str
    explanation: str
    tables_used: list[str] = Field(default_factory=list)
    chart_hint: str = "table_only"
    confidence: ConfidenceLevel = "medium"


SQL_GENERATION_TOOL_NAME = "submit_sql"

SQL_GENERATION_TOOL: dict[str, Any] = {
    "name": SQL_GENERATION_TOOL_NAME,
    "description": (
        "Submit the generated read-only SQL query along with metadata about "
        "the query. You must call this tool — do not respond with free text."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "A single read-only SELECT statement.",
            },
            "explanation": {
                "type": "string",
                "description": "Plain-language summary of what the query returns.",
            },
            "tables_used": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Table names referenced in the query.",
            },
            "chart_hint": {
                "type": "string",
                "description": (
                    "Suggested visualization: bar, line, area, scatter, pie, "
                    "stat_card, or table_only."
                ),
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "Self-assessed confidence in the generated SQL.",
            },
        },
        "required": ["sql", "explanation", "tables_used", "chart_hint", "confidence"],
    },
}
