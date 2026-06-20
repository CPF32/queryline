"""Chart specification model for Recharts rendering.

See CONTRACTS.md §4.8.
"""

from enum import Enum
from typing import Self

from pydantic import BaseModel, Field


class ChartType(str, Enum):
    """Supported visualization types."""

    BAR = "bar"
    LINE = "line"
    AREA = "area"
    SCATTER = "scatter"
    PIE = "pie"
    STAT_CARD = "stat_card"
    TABLE_ONLY = "table_only"


class ChartSpec(BaseModel):
    """Structured chart definition produced by the chart-spec LLM call."""

    chart_type: ChartType
    x_field: str | None = None
    y_fields: list[str] = Field(default_factory=list)
    series_field: str | None = None
    aggregation_applied: bool
    title: str

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)
