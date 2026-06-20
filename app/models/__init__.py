"""Pydantic domain models.

See CONTRACTS.md §4 for field definitions and serialization contracts.
"""

from app.models.chart_spec import ChartSpec, ChartType
from app.models.data_source import DataSource
from app.models.glossary import GlossaryTerm
from app.models.query_log import QueryLogEntry
from app.models.query_result import QueryColumnMeta, QueryResult
from app.models.schema import SchemaColumn, SchemaRelationship, SchemaTable
from app.models.sql_example import SqlExample

__all__ = [
    "ChartSpec",
    "ChartType",
    "DataSource",
    "GlossaryTerm",
    "QueryColumnMeta",
    "QueryLogEntry",
    "QueryResult",
    "SchemaColumn",
    "SchemaRelationship",
    "SchemaTable",
    "SqlExample",
]
