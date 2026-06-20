"""Pydantic request/response schemas for admin API validation."""

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class CreateDataSourceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    connector_type: str | None = None
    engine_type: str | None = None
    connection_config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

    @field_validator("connector_type", "engine_type", mode="before")
    @classmethod
    def strip_connector(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def require_connector_type(self):
        if not (self.connector_type or self.engine_type):
            raise ValueError("connector_type or engine_type is required.")
        return self

    def resolved_connector_type(self) -> str:
        return self.connector_type or self.engine_type  # type: ignore[return-value]


class UpdateDataSourceRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    connector_type: str | None = None
    engine_type: str | None = None
    connection_config: dict[str, Any] | None = None
    is_active: bool | None = None

    def resolved_connector_type(self) -> str | None:
        return self.connector_type or self.engine_type


class TestConnectionRequest(BaseModel):
    connector_type: str | None = None
    engine_type: str | None = None
    connection_config: dict[str, Any] = Field(default_factory=dict)

    def resolved_connector_type(self) -> str:
        connector = self.connector_type or self.engine_type
        if not connector:
            raise ValueError("connector_type or engine_type is required.")
        return connector


class TableSelection(BaseModel):
    schema_name: str | None = None
    table_name: str = Field(min_length=1)
    object_type: str = "table"


class OnboardSchemaTablesRequest(BaseModel):
    tables: list[TableSelection] = Field(min_length=1)


class ImportSchemaRequest(BaseModel):
    mode: str = "merge"
    include_tables: list[str] | None = None
    exclude_tables: list[str] | None = None


class UpdateSchemaTableRequest(BaseModel):
    display_name: str | None = None
    description: str | None = None
    is_included_in_prompt: bool | None = None


class UpdateSchemaColumnRequest(BaseModel):
    display_name: str | None = None
    description: str | None = None
    is_pii: bool | None = None
    is_excluded_from_prompt: bool | None = None


class CreateSchemaRelationshipRequest(BaseModel):
    constraint_name: str = Field(min_length=1)
    source_table_id: str
    source_column_id: str
    target_table_id: str
    target_column_id: str
    relationship_type: str = "foreign_key"


class CreateGlossaryTermRequest(BaseModel):
    term: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    sql_expression: str | None = None
    table_id: str | None = None
    column_id: str | None = None


class UpdateGlossaryTermRequest(BaseModel):
    term: str | None = Field(default=None, min_length=1)
    definition: str | None = Field(default=None, min_length=1)
    sql_expression: str | None = None
    table_id: str | None = None
    column_id: str | None = None


class CreateSqlExampleRequest(BaseModel):
    question: str = Field(min_length=1)
    sql: str = Field(min_length=1)
    notes: str | None = None


class UpdateSqlExampleRequest(BaseModel):
    question: str | None = Field(default=None, min_length=1)
    sql: str | None = Field(default=None, min_length=1)
    notes: str | None = None


class PromoteQueryLogRequest(BaseModel):
    notes: str | None = None
