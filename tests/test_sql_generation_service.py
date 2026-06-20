"""Unit tests for SQL generation service."""

from __future__ import annotations

from typing import Any

import pytest

from app.clients.claude_client import ClaudeClient
from app.schemas.metadata_bundle import (
    MetadataBundle,
    MetadataBundleColumn,
    MetadataBundleExample,
    MetadataBundleGlossaryTerm,
    MetadataBundleTable,
)
from app.schemas.sql_generation import SqlGenerationToolOutput
from app.services import metadata_retrieval
from app.services.metadata_retrieval import MetadataEmbeddingCache
from app.services.sql_generation_service import (
    MAX_GENERATION_ATTEMPTS,
    build_system_prompt,
    build_user_prompt,
    generate_sql,
)


DATA_SOURCE_ID = "11111111-1111-4111-8111-111111111111"


def _make_column(name: str, description: str = "") -> MetadataBundleColumn:
    return MetadataBundleColumn(
        id=f"col-{name}",
        name=name,
        data_type="varchar",
        is_nullable=True,
        is_primary_key=False,
        description=description or None,
    )


def _make_table(
    table_name: str,
    *,
    description: str = "",
    columns: list[MetadataBundleColumn] | None = None,
) -> MetadataBundleTable:
    return MetadataBundleTable(
        id=f"tbl-{table_name}",
        table_name=table_name,
        qualified_name=table_name,
        description=description or None,
        columns=columns
        or [
            _make_column("id", "Primary identifier"),
            _make_column("region", "Sales region"),
            _make_column("revenue", "Order revenue in USD"),
        ],
    )


def _make_bundle(**overrides: Any) -> MetadataBundle:
    orders = _make_table("orders", description="One row per order")
    regions = _make_table(
        "regions",
        description="Geographic regions",
        columns=[
            _make_column("id"),
            _make_column("name", "Region name"),
        ],
    )
    defaults = dict(
        data_source_id=DATA_SOURCE_ID,
        data_source_name="Analytics Warehouse",
        dialect_name="postgres",
        tables=[orders, regions],
        relationships=[],
        glossary=[
            MetadataBundleGlossaryTerm(
                id="term-active-customer",
                term="Active Customer",
                definition="Customer with an order in the last 90 days.",
                sql_expression="EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id)",
                table_id="tbl-orders",
                table_name="orders",
            )
        ],
        examples=[
            MetadataBundleExample(
                id="ex-1",
                question="Total revenue by region",
                sql="SELECT region, SUM(revenue) AS total_revenue FROM orders GROUP BY region",
                notes="Aggregate example",
            )
        ],
    )
    defaults.update(overrides)
    return MetadataBundle(**defaults)


class MockClaudeClient:
    """Returns canned tool outputs in call order."""

    def __init__(self, responses: list[SqlGenerationToolOutput | Exception]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, str]] = []

    def generate_sql_tool_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> SqlGenerationToolOutput:
        self.calls.append(
            {"system_prompt": system_prompt, "user_prompt": user_prompt}
        )
        if not self._responses:
            raise RuntimeError("No canned responses remaining.")
        next_response = self._responses.pop(0)
        if isinstance(next_response, Exception):
            raise next_response
        return next_response


@pytest.fixture
def bundle() -> MetadataBundle:
    return _make_bundle()


@pytest.fixture
def cache() -> MetadataEmbeddingCache:
    return MetadataEmbeddingCache()


def test_clean_first_pass_success(bundle: MetadataBundle, cache: MetadataEmbeddingCache) -> None:
    mock_client = MockClaudeClient(
        [
            SqlGenerationToolOutput(
                sql=(
                    "SELECT region, SUM(revenue) AS total_revenue "
                    "FROM orders GROUP BY region LIMIT 1000"
                ),
                explanation="Aggregates revenue by region.",
                tables_used=["orders"],
                chart_hint="bar",
                confidence="high",
            )
        ]
    )

    result = generate_sql(
        "Show total revenue by region",
        DATA_SOURCE_ID,
        conversation_history=[],
        retry_context=None,
        metadata_bundle=bundle,
        claude_client=mock_client,
        embedding_cache=cache,
    )

    assert result.success is True
    assert result.sql is not None
    assert "SUM(revenue)" in result.sql
    assert result.tables_used == ["orders"]
    assert result.chart_hint == "bar"
    assert result.confidence == "high"
    assert result.attempt_number == 1
    assert len(mock_client.calls) == 1

    system_prompt = mock_client.calls[0]["system_prompt"]
    assert "Generate valid postgres SQL" in system_prompt
    assert "Never use SELECT *" in system_prompt
    assert "LIMIT N" in system_prompt


def test_retry_then_success(bundle: MetadataBundle, cache: MetadataEmbeddingCache) -> None:
    first_sql = "SELECT region, SUM(reveneu) AS total_revenue FROM orders GROUP BY region"
    corrected_sql = (
        "SELECT region, SUM(revenue) AS total_revenue "
        "FROM orders GROUP BY region LIMIT 1000"
    )

    first_client = MockClaudeClient(
        [
            SqlGenerationToolOutput(
                sql=first_sql,
                explanation="Initial attempt with typo.",
                tables_used=["orders"],
                chart_hint="bar",
                confidence="medium",
            )
        ]
    )
    first_result = generate_sql(
        "Show total revenue by region",
        DATA_SOURCE_ID,
        metadata_bundle=bundle,
        claude_client=first_client,
        embedding_cache=cache,
    )
    assert first_result.success is True
    assert first_result.sql == first_sql

    retry_client = MockClaudeClient(
        [
            SqlGenerationToolOutput(
                sql=corrected_sql,
                explanation="Fixed misspelled revenue column.",
                tables_used=["orders"],
                chart_hint="bar",
                confidence="high",
            )
        ]
    )
    retry_result = generate_sql(
        "Show total revenue by region",
        DATA_SOURCE_ID,
        retry_context={
            "previous_sql": first_result.sql,
            "execution_error": 'column "reveneu" does not exist',
            "attempt_number": 2,
        },
        metadata_bundle=bundle,
        claude_client=retry_client,
        embedding_cache=cache,
    )

    assert retry_result.success is True
    assert retry_result.sql == corrected_sql
    assert retry_result.attempt_number == 2
    assert "Previous SQL:" in retry_client.calls[0]["user_prompt"]
    assert 'column "reveneu" does not exist' in retry_client.calls[0]["user_prompt"]


def test_all_retries_failed(bundle: MetadataBundle, cache: MetadataEmbeddingCache) -> None:
    result = generate_sql(
        "Show total revenue by region",
        DATA_SOURCE_ID,
        retry_context={
            "previous_sql": "SELECT 1",
            "execution_error": "relation does not exist",
            "attempt_number": MAX_GENERATION_ATTEMPTS + 1,
        },
        metadata_bundle=bundle,
        claude_client=MockClaudeClient([]),
        embedding_cache=cache,
    )

    assert result.success is False
    assert result.sql is None
    assert "Couldn't generate a valid query after 3 attempts" in result.explanation
    assert result.error_message is not None


def test_tsql_dialect_rules_in_prompt() -> None:
    prompt = build_system_prompt("tsql")
    dialect_section = prompt.split("Global rules")[0]
    assert "Generate valid tsql SQL" in prompt
    assert "Use TOP N for row limits" in dialect_section
    assert "LIMIT N for postgres" not in dialect_section


def test_conversation_history_included(bundle: MetadataBundle) -> None:
    prompt = build_user_prompt(
        question="What about last month?",
        bundle=bundle,
        selected_tables=bundle.tables,
        selected_examples=bundle.examples,
        matched_glossary_terms=[],
        conversation_history=[
            {"role": "user", "content": "Show revenue by region"},
            {"role": "assistant", "content": "Here is revenue by region."},
        ],
        retry_context=None,
    )
    assert "Conversation history" in prompt
    assert "Show revenue by region" in prompt


def test_table_retrieval_when_many_tables(cache: MetadataEmbeddingCache) -> None:
    revenue_table = _make_table(
        "monthly_revenue",
        description="Monthly revenue totals by product category",
        columns=[
            _make_column("category", "Product category"),
            _make_column("month", "Calendar month"),
            _make_column("revenue", "Revenue amount"),
        ],
    )
    unrelated_tables = [
        _make_table(
            f"archive_{index}",
            description=f"Unrelated archive table {index}",
            columns=[_make_column("payload")],
        )
        for index in range(20)
    ]
    large_bundle = _make_bundle(tables=[revenue_table, *unrelated_tables])

    selected, matched = cache.retrieve_tables(
        large_bundle,
        "monthly revenue by product category",
    )

    selected_names = {table.table_name for table in selected}
    assert "monthly_revenue" in selected_names
    assert len(selected) <= metadata_retrieval.TOP_N_TABLES
    assert matched == []


def test_glossary_literal_match_adds_table(cache: MetadataEmbeddingCache) -> None:
    glossary_table = _make_table(
        "customers",
        description="Customer master",
        columns=[_make_column("id"), _make_column("name")],
    )
    filler_tables = [
        _make_table(
            f"table_{index}",
            description="Generic filler",
            columns=[_make_column("value")],
        )
        for index in range(20)
    ]
    bundle = _make_bundle(
        tables=[glossary_table, *filler_tables],
        glossary=[
            MetadataBundleGlossaryTerm(
                id="term-1",
                term="Active Customer",
                definition="Customer with recent orders.",
                table_id="tbl-customers",
                table_name="customers",
            )
        ],
    )

    selected, matched = cache.retrieve_tables(
        bundle,
        "How many active customers do we have?",
    )

    assert "Active Customer" in matched
    assert any(table.table_name == "customers" for table in selected)


def test_claude_failure_returns_error(bundle: MetadataBundle, cache: MetadataEmbeddingCache) -> None:
    mock_client = MockClaudeClient([RuntimeError("API unavailable")])

    result = generate_sql(
        "Show total revenue by region",
        DATA_SOURCE_ID,
        metadata_bundle=bundle,
        claude_client=mock_client,
        embedding_cache=cache,
    )

    assert result.success is False
    assert result.sql is None
    assert "API unavailable" in (result.error_message or "")
