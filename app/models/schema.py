"""Schema metadata models for tables, columns, and relationships.

See CONTRACTS.md §4.2–§4.4.
"""

from typing import Self

from pydantic import BaseModel


class SchemaTable(BaseModel):
    """Persisted schema object metadata scoped to a data source."""

    id: str
    data_source_id: str
    schema_name: str | None = None
    table_name: str
    object_type: str = "table"
    display_name: str | None = None
    description: str | None = None
    is_included_in_prompt: bool = True
    row_count_estimate: int | None = None
    definition: str | None = None
    return_type: str | None = None
    created_at: str
    updated_at: str
    user_id: str | None = None
    workspace_id: str | None = None

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)


class SchemaColumn(BaseModel):
    """Persisted column metadata belonging to a schema table."""

    id: str
    table_id: str
    column_name: str
    display_name: str | None = None
    description: str | None = None
    data_type: str
    is_nullable: bool
    is_primary_key: bool
    ordinal_position: int
    sample_distinct_values: list[str] | None = None
    is_pii: bool = False
    is_excluded_from_prompt: bool = False
    created_at: str
    updated_at: str
    user_id: str | None = None
    workspace_id: str | None = None

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)


class SchemaRelationship(BaseModel):
    """Persisted foreign-key (or other) relationship between schema columns."""

    id: str
    data_source_id: str
    constraint_name: str
    source_table_id: str
    source_column_id: str
    target_table_id: str
    target_column_id: str
    relationship_type: str
    created_at: str
    updated_at: str
    user_id: str | None = None
    workspace_id: str | None = None

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)
