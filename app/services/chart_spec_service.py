"""Chart specification generation via Claude structured output.

Produces ChartSpec JSON from user question, SQL, and query result shape.
Does not render charts.

See CONTRACTS.md §4.8, §5.10, and §6.
"""

from __future__ import annotations

import json

from app.clients.claude_client import ClaudeClient
from app.clients.llm_factory import get_llm_client, llm_api_key_configured
from app.models.chart_spec import ChartSpec, ChartType
from app.models.query_result import QueryColumnMeta

ColumnMeta = QueryColumnMeta

SAMPLE_ROW_CAP = 20
LARGE_RESULT_ROW_THRESHOLD = 500
LOW_CARDINALITY_DISTINCT_CAP = 20
OBVIOUS_GROUPING_DISTINCT_MAX = 12

_NUMERIC_TYPE_TOKENS = frozenset(
    {
        "int",
        "integer",
        "bigint",
        "smallint",
        "tinyint",
        "float",
        "double",
        "decimal",
        "numeric",
        "number",
        "real",
        "money",
    }
)

_CATEGORICAL_TYPE_TOKENS = frozenset(
    {
        "str",
        "string",
        "text",
        "varchar",
        "char",
        "character",
        "uuid",
        "bool",
        "boolean",
    }
)

_SYSTEM_PROMPT = """\
You are a data visualization assistant. Given query result metadata, a small
sample of rows, and the user's original question, choose the best chart type
and field mapping.

Rules:
- Prefer bar charts for categorical breakdowns; line/area for time series.
- Use pie only for a single measure split across a few categories (<=8).
- Use stat_card only for a single scalar metric (one row, one number).
- Use table_only when the data is row-level detail unsuitable for charting.
- x_field, y_fields, and series_field MUST be exact column names from the input.
- Set aggregation_applied true when measures are already aggregated in SQL.
"""


def generate_chart_spec(
    columns: list[ColumnMeta],
    sample_rows: list[dict],
    row_count: int,
    original_question: str,
    chart_hint: str | None = None,
    *,
    claude_client: ClaudeClient | None = None,
) -> ChartSpec:
    """Return a ChartSpec using deterministic rules or a Claude tool-use call."""
    column_names = {column.name for column in columns}

    stat_card = _try_stat_card_fallback(columns, row_count, original_question)
    if stat_card is not None:
        return stat_card

    table_only = _try_table_only_fallback(columns, sample_rows, row_count, original_question)
    if table_only is not None:
        return table_only

    client = claude_client or get_llm_client()
    try:
        llm_spec = client.generate_chart_spec_tool_output(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=_build_user_prompt(
                columns=columns,
                sample_rows=sample_rows[:SAMPLE_ROW_CAP],
                row_count=row_count,
                original_question=original_question,
                chart_hint=chart_hint,
            ),
        )
    except RuntimeError as exc:
        if not llm_api_key_configured() or "API_KEY" in str(exc):
            return _table_only_spec(original_question)
        raise
    return _validate_chart_spec(llm_spec, column_names, original_question)


def _try_stat_card_fallback(
    columns: list[ColumnMeta],
    row_count: int,
    original_question: str,
) -> ChartSpec | None:
    if row_count != 1:
        return None

    numeric_columns = [column for column in columns if _is_numeric_type(column.type)]
    if len(numeric_columns) != 1:
        return None

    measure = numeric_columns[0].name
    return ChartSpec(
        chart_type=ChartType.STAT_CARD,
        x_field=None,
        y_fields=[measure],
        series_field=None,
        aggregation_applied=True,
        title=_default_title(original_question, measure),
    )


def _try_table_only_fallback(
    columns: list[ColumnMeta],
    sample_rows: list[dict],
    row_count: int,
    original_question: str,
) -> ChartSpec | None:
    if row_count <= LARGE_RESULT_ROW_THRESHOLD:
        return None
    if _has_obvious_low_cardinality_grouping_column(columns, sample_rows):
        return None

    return _table_only_spec(original_question)


def _has_obvious_low_cardinality_grouping_column(
    columns: list[ColumnMeta],
    sample_rows: list[dict],
) -> bool:
    if not sample_rows:
        return False

    for column in columns:
        if _is_numeric_type(column.type):
            continue
        if not _is_categorical_type(column.type):
            continue

        values = [row.get(column.name) for row in sample_rows if column.name in row]
        non_null_values = [value for value in values if value is not None]
        if not non_null_values:
            continue

        distinct_count = len(set(non_null_values))
        if distinct_count <= OBVIOUS_GROUPING_DISTINCT_MAX:
            return True
        if distinct_count <= LOW_CARDINALITY_DISTINCT_CAP and distinct_count < len(non_null_values):
            return True

    return False


def _validate_chart_spec(
    spec: ChartSpec,
    column_names: set[str],
    original_question: str,
) -> ChartSpec:
    if spec.chart_type == ChartType.TABLE_ONLY:
        return spec

    if not _fields_exist(spec, column_names):
        return _table_only_spec(original_question)

    if spec.chart_type == ChartType.STAT_CARD:
        if not spec.y_fields:
            return _table_only_spec(original_question)
        return spec

    if spec.chart_type in {ChartType.PIE, ChartType.SCATTER}:
        if not spec.x_field or not spec.y_fields:
            return _table_only_spec(original_question)
        return spec

    if spec.chart_type in {ChartType.BAR, ChartType.LINE, ChartType.AREA}:
        if not spec.x_field or not spec.y_fields:
            return _table_only_spec(original_question)
        return spec

    return spec


def _fields_exist(spec: ChartSpec, column_names: set[str]) -> bool:
    if spec.x_field is not None and spec.x_field not in column_names:
        return False
    if spec.series_field is not None and spec.series_field not in column_names:
        return False
    if not spec.y_fields:
        return False
    return all(field in column_names for field in spec.y_fields)


def _is_numeric_type(type_name: str) -> bool:
    normalized = type_name.strip().lower()
    base = normalized.split("(")[0].strip()
    return base in _NUMERIC_TYPE_TOKENS


def _is_categorical_type(type_name: str) -> bool:
    normalized = type_name.strip().lower()
    base = normalized.split("(")[0].strip()
    if base in _CATEGORICAL_TYPE_TOKENS:
        return True
    return not _is_numeric_type(type_name) and "date" not in base and "time" not in base


def _table_only_spec(original_question: str) -> ChartSpec:
    return ChartSpec(
        chart_type=ChartType.TABLE_ONLY,
        x_field=None,
        y_fields=[],
        series_field=None,
        aggregation_applied=False,
        title=_default_title(original_question),
    )


def _default_title(original_question: str, suffix: str | None = None) -> str:
    title = original_question.strip().rstrip("?.!")
    if suffix:
        return f"{title} — {suffix}" if title else suffix
    return title or "Query Results"


def _build_user_prompt(
    *,
    columns: list[ColumnMeta],
    sample_rows: list[dict],
    row_count: int,
    original_question: str,
    chart_hint: str | None,
) -> str:
    payload = {
        "original_question": original_question,
        "chart_hint": chart_hint,
        "row_count": row_count,
        "columns": [{"name": column.name, "type": column.type} for column in columns],
        "sample_rows": sample_rows,
    }
    return json.dumps(payload, indent=2, default=str)
