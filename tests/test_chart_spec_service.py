"""Tests for chart spec generation fallbacks and LLM path."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.models.chart_spec import ChartSpec, ChartType
from app.models.query_result import QueryColumnMeta
from app.services import chart_spec_service
from app.services.chart_spec_service import generate_chart_spec


@dataclass
class FakeClaudeClient:
    calls: list[tuple[str, str]] = field(default_factory=list)
    response: ChartSpec | None = None

    def generate_chart_spec_tool_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> ChartSpec:
        self.calls.append((system_prompt, user_prompt))
        if self.response is None:
            raise AssertionError("FakeClaudeClient.response was not configured")
        return self.response


def test_stat_card_fallback_single_numeric_row() -> None:
    columns = [QueryColumnMeta(name="total_revenue", type="float")]
    sample_rows = [{"total_revenue": 125000.0}]
    client = FakeClaudeClient(
        response=ChartSpec(
            chart_type=ChartType.BAR,
            x_field="region",
            y_fields=["total_revenue"],
            series_field=None,
            aggregation_applied=True,
            title="Should not be used",
        )
    )

    spec = generate_chart_spec(
        columns=columns,
        sample_rows=sample_rows,
        row_count=1,
        original_question="What is total revenue?",
        chart_hint=None,
        claude_client=client,
    )

    assert spec.chart_type == ChartType.STAT_CARD
    assert spec.y_fields == ["total_revenue"]
    assert spec.aggregation_applied is True
    assert client.calls == []


def test_table_only_fallback_for_large_unaggregated_results() -> None:
    columns = [
        QueryColumnMeta(name="order_id", type="string"),
        QueryColumnMeta(name="amount", type="float"),
    ]
    sample_rows = [
        {"order_id": f"ORD-{index}", "amount": float(index)}
        for index in range(20)
    ]
    client = FakeClaudeClient(
        response=ChartSpec(
            chart_type=ChartType.BAR,
            x_field="order_id",
            y_fields=["amount"],
            series_field=None,
            aggregation_applied=False,
            title="Should not be used",
        )
    )

    spec = generate_chart_spec(
        columns=columns,
        sample_rows=sample_rows,
        row_count=1200,
        original_question="List all orders",
        chart_hint="bar",
        claude_client=client,
    )

    assert spec.chart_type == ChartType.TABLE_ONLY
    assert spec.y_fields == []
    assert client.calls == []


def test_large_result_with_grouping_column_defers_to_llm() -> None:
    columns = [
        QueryColumnMeta(name="region", type="string"),
        QueryColumnMeta(name="total_revenue", type="float"),
    ]
    sample_rows = [
        {"region": region, "total_revenue": value}
        for region, value in [
            ("North", 100.0),
            ("South", 200.0),
            ("East", 150.0),
            ("West", 175.0),
        ]
    ]
    expected = ChartSpec(
        chart_type=ChartType.BAR,
        x_field="region",
        y_fields=["total_revenue"],
        series_field=None,
        aggregation_applied=True,
        title="Revenue by Region",
    )
    client = FakeClaudeClient(response=expected)

    spec = generate_chart_spec(
        columns=columns,
        sample_rows=sample_rows,
        row_count=600,
        original_question="Show revenue by region",
        chart_hint="bar",
        claude_client=client,
    )

    assert spec == expected
    assert len(client.calls) == 1


def test_invalid_llm_field_references_fall_back_to_table_only() -> None:
    columns = [
        QueryColumnMeta(name="region", type="string"),
        QueryColumnMeta(name="total_revenue", type="float"),
    ]
    sample_rows = [
        {"region": "North", "total_revenue": 100.0},
        {"region": "South", "total_revenue": 200.0},
    ]
    client = FakeClaudeClient(
        response=ChartSpec(
            chart_type=ChartType.BAR,
            x_field="missing_region",
            y_fields=["total_revenue"],
            series_field=None,
            aggregation_applied=True,
            title="Revenue by Region",
        )
    )

    spec = generate_chart_spec(
        columns=columns,
        sample_rows=sample_rows,
        row_count=2,
        original_question="Show revenue by region",
        chart_hint="bar",
        claude_client=client,
    )

    assert spec.chart_type == ChartType.TABLE_ONLY
    assert len(client.calls) == 1


def test_llm_driven_bar_chart_when_no_fallback_applies() -> None:
    columns = [
        QueryColumnMeta(name="region", type="string"),
        QueryColumnMeta(name="total_revenue", type="float"),
    ]
    sample_rows = [
        {"region": "North", "total_revenue": 125000.0},
        {"region": "South", "total_revenue": 98000.0},
    ]
    expected = ChartSpec(
        chart_type=ChartType.BAR,
        x_field="region",
        y_fields=["total_revenue"],
        series_field=None,
        aggregation_applied=True,
        title="Total Revenue by Region",
    )
    client = FakeClaudeClient(response=expected)

    spec = generate_chart_spec(
        columns=columns,
        sample_rows=sample_rows,
        row_count=2,
        original_question="Show me total revenue by region for Q1 2026",
        chart_hint="bar",
        claude_client=client,
    )

    assert spec == expected
    assert len(client.calls) == 1
    _, user_prompt = client.calls[0]
    assert '"row_count": 2' in user_prompt
    assert "total_revenue" in user_prompt
    assert "Show me total revenue by region for Q1 2026" in user_prompt


def test_sample_rows_capped_before_llm_call(monkeypatch) -> None:
    monkeypatch.setattr(chart_spec_service, "SAMPLE_ROW_CAP", 3)

    columns = [QueryColumnMeta(name="value", type="integer")]
    sample_rows = [{"value": index} for index in range(10)]
    client = FakeClaudeClient(
        response=ChartSpec(
            chart_type=ChartType.LINE,
            x_field="value",
            y_fields=["value"],
            series_field=None,
            aggregation_applied=False,
            title="Values",
        )
    )

    generate_chart_spec(
        columns=columns,
        sample_rows=sample_rows,
        row_count=10,
        original_question="Show values",
        claude_client=client,
    )

    _, user_prompt = client.calls[0]
    payload = json.loads(user_prompt)
    assert len(payload["sample_rows"]) == 3


def test_missing_api_key_falls_back_to_table_only(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")

    columns = [
        QueryColumnMeta(name="name", type="string"),
        QueryColumnMeta(name="order_count", type="integer"),
    ]
    sample_rows = [
        {"name": "Acme Corp", "order_count": 2},
        {"name": "Beta LLC", "order_count": 1},
    ]

    spec = generate_chart_spec(
        columns=columns,
        sample_rows=sample_rows,
        row_count=2,
        original_question="How many orders per customer?",
    )

    assert spec.chart_type == ChartType.TABLE_ONLY
