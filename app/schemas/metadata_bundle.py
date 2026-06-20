"""Curated metadata package consumed by the text-to-SQL agent (Agent 5)."""

from pydantic import BaseModel, Field


class MetadataBundleColumn(BaseModel):
    id: str
    name: str
    display_name: str | None = None
    description: str | None = None
    data_type: str
    is_nullable: bool
    is_primary_key: bool
    is_pii: bool = False
    is_excluded_from_prompt: bool = False
    sample_distinct_values: list[str] | None = None


class MetadataBundleTable(BaseModel):
    id: str
    schema_name: str | None = None
    table_name: str
    qualified_name: str
    object_type: str = "table"
    display_name: str | None = None
    description: str | None = None
    row_count_estimate: int | None = None
    definition: str | None = None
    return_type: str | None = None
    columns: list[MetadataBundleColumn] = Field(default_factory=list)


class MetadataBundleRelationship(BaseModel):
    id: str
    constraint_name: str
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    relationship_type: str


class MetadataBundleGlossaryTerm(BaseModel):
    id: str
    term: str
    definition: str
    sql_expression: str | None = None
    table_id: str | None = None
    column_id: str | None = None
    table_name: str | None = None
    column_name: str | None = None


class MetadataBundleExample(BaseModel):
    id: str
    question: str
    sql: str
    notes: str | None = None
    source: str = "manual"


class MetadataBundle(BaseModel):
    """Full prompt context for SQL generation for one data source."""

    data_source_id: str
    data_source_name: str
    dialect_name: str
    tables: list[MetadataBundleTable] = Field(default_factory=list)
    relationships: list[MetadataBundleRelationship] = Field(default_factory=list)
    glossary: list[MetadataBundleGlossaryTerm] = Field(default_factory=list)
    examples: list[MetadataBundleExample] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")
