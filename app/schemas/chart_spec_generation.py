"""Types and tool schema for chart-spec generation via Claude."""

from typing import Any

from app.models.chart_spec import ChartSpec, ChartType

CHART_SPEC_TOOL_NAME = "submit_chart_spec"

CHART_TYPE_VALUES = [t.value for t in ChartType]

CHART_SPEC_TOOL: dict[str, Any] = {
    "name": CHART_SPEC_TOOL_NAME,
    "description": (
        "Submit the chart specification for visualizing query results. "
        "You must call this tool — do not respond with free text."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "chart_type": {
                "type": "string",
                "enum": CHART_TYPE_VALUES,
                "description": "Visualization type best suited to the data shape.",
            },
            "x_field": {
                "type": "string",
                "description": "Column name for the x-axis or category labels. Omit for stat_card/table_only.",
            },
            "y_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "One or more measure column names.",
            },
            "series_field": {
                "type": "string",
                "description": "Optional column for series/color grouping.",
            },
            "aggregation_applied": {
                "type": "boolean",
                "description": "True when SQL already aggregated the measures.",
            },
            "title": {
                "type": "string",
                "description": "Short chart title derived from the user question.",
            },
        },
        "required": ["chart_type", "y_fields", "aggregation_applied", "title"],
    },
}


def parse_chart_spec_tool_output(raw: dict[str, Any]) -> ChartSpec:
    """Parse a tool input dict into a validated ChartSpec."""
    normalized = dict(raw)
    if normalized.get("x_field") == "":
        normalized["x_field"] = None
    if normalized.get("series_field") == "":
        normalized["series_field"] = None
    return ChartSpec.model_validate(normalized)
