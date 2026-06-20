"""Abstract adapter interface and adapter-level result types.

See CONTRACTS.md §3 for the full specification.
"""

from abc import ABC, abstractmethod
from typing import Any, Self

from pydantic import BaseModel, Field


class ConnectionTestResult(BaseModel):
    """Outcome of a connection health check."""

    success: bool
    message: str
    latency_ms: float | None = None

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)


class ReadOnlyVerificationResult(BaseModel):
    """Outcome of a one-time read-only grant check."""

    success: bool
    message: str

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)


class QueryColumnMeta(BaseModel):
    """Metadata for a single column in a query result set."""

    name: str
    type: str

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)


class QueryResult(BaseModel):
    """Result of a read-only SQL execution."""

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


class SchemaColumnDraft(BaseModel):
    """Column shape returned by live schema introspection."""

    column_name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool
    ordinal_position: int
    sample_distinct_values: list[str] | None = None

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)


class SchemaRelationshipDraft(BaseModel):
    """Relationship shape returned by live schema introspection."""

    constraint_name: str
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    relationship_type: str = "foreign_key"

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)


SchemaObjectType = str  # "table" | "view" | "function" | "procedure"

SCHEMA_OBJECT_TYPES = frozenset({"table", "view", "function", "procedure"})


class SchemaTableDraft(BaseModel):
    """Schema object shape returned by live schema introspection.

    Despite the name, this covers tables, views, functions, and procedures.
    ``table_name`` holds the object name for all types.
    """

    schema_name: str | None = None
    table_name: str
    object_type: str = "table"
    row_count_estimate: int | None = None
    definition: str | None = None
    return_type: str | None = None
    columns: list[SchemaColumnDraft] = Field(default_factory=list)
    relationships: list[SchemaRelationshipDraft] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)


class SchemaSnapshot(BaseModel):
    """Full schema introspection result from an adapter."""

    tables: list[SchemaTableDraft] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)


class DataSourceAdapter(ABC):
    """Engine-specific bridge for connection, introspection, and read-only execution.

    Implementations must not leak engine details above this layer. Callers use
    ``get_dialect_name()`` for sqlglot-compatible dialect strings.
    """

    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        """Verify connectivity and credentials."""
        ...

    @abstractmethod
    def verify_readonly_grants(self) -> ReadOnlyVerificationResult:
        """Verify the DB login has no write or DDL privileges.

        Must be run once when an admin saves a connection. Successful verification
        is required before ``execute_readonly_query`` will run.
        """
        ...

    @abstractmethod
    def introspect_schema(self) -> SchemaSnapshot:
        """Discover tables, views, routines, columns, keys, relationships, and sample values."""
        ...

    @abstractmethod
    def execute_readonly_query(
        self,
        sql: str,
        max_rows: int,
        timeout_seconds: int,
    ) -> QueryResult:
        """Execute a validated read-only SELECT and return rows."""
        ...

    @abstractmethod
    def get_dialect_name(self) -> str:
        """Return a valid sqlglot dialect string (e.g. 'tsql', 'postgres')."""
        ...

    @classmethod
    @abstractmethod
    def get_connection_form_schema(cls) -> dict:
        """Return JSON-Schema-like dict for admin connection form rendering."""
        ...
