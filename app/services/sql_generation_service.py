"""Natural-language to SQL generation via Claude structured output.

Assembles prompt context from dialect_name, schema metadata, glossary, and
examples. Must not reference engine-specific SQL beyond dialect_name.

See CONTRACTS.md §5.8 and §6.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from app.clients.claude_client import ClaudeClient
from app.clients.llm_factory import get_llm_client
from app.clients.sql_generation_stream import stream_sql_generation
from app.errors import NotFoundError
from app.schemas.metadata_bundle import (
    MetadataBundle,
    MetadataBundleColumn,
    MetadataBundleExample,
    MetadataBundleGlossaryTerm,
    MetadataBundleRelationship,
    MetadataBundleTable,
)
from app.schemas.sql_generation import SqlGenerationResult, SqlGenerationToolOutput
from app.services.feedback_service import get_negative_feedback_context
from app.services.metadata_retrieval import MetadataEmbeddingCache, get_embedding_cache
from app.services.metadata_service import build_metadata_bundle

MAX_GENERATION_ATTEMPTS = 3
DEFAULT_ROW_LIMIT = 1000

DIALECT_RULES: dict[str, list[str]] = {
    "postgres": [
        "Use LIMIT N for row limits (e.g. LIMIT 1000).",
        "Use double quotes for identifiers when quoting is required.",
        "Use single quotes for string literals.",
        "Date functions: CURRENT_DATE, date_trunc, INTERVAL 'N days'.",
    ],
    "mysql": [
        "Use LIMIT N for row limits (e.g. LIMIT 1000).",
        "Use backticks for identifiers when quoting is required.",
        "Use single quotes for string literals.",
    ],
    "sqlite": [
        "Use LIMIT N for row limits (e.g. LIMIT 1000).",
        "Use double quotes for identifiers when quoting is required.",
        "Use single quotes for string literals.",
    ],
    "tsql": [
        "Use TOP N for row limits (e.g. SELECT TOP 1000 ...).",
        "Use square brackets for identifiers when quoting is required.",
        "Use single quotes for string literals.",
        "Use T-SQL date functions such as GETDATE(), DATEADD, DATEDIFF.",
    ],
}

DEFAULT_DIALECT_RULES = [
    "Use the target dialect's standard row-limit syntax.",
    "Quote identifiers according to the target dialect.",
    "Use single quotes for string literals.",
]


def _get_claude_client() -> ClaudeClient:
    return get_llm_client()


def _attempt_number(retry_context: dict[str, Any] | None) -> int:
    if not retry_context:
        return 1
    return int(retry_context.get("attempt_number", 1))


@dataclass(frozen=True)
class _SqlGenerationContext:
    attempt: int
    matched_glossary_terms: list[str]
    system_prompt: str
    user_prompt: str


def _prepare_sql_generation(
    question: str,
    data_source_id: str,
    conversation_history: list[dict[str, str]] | None = None,
    retry_context: dict[str, Any] | None = None,
    *,
    metadata_bundle: MetadataBundle | None = None,
    embedding_cache: MetadataEmbeddingCache | None = None,
) -> SqlGenerationResult | _SqlGenerationContext:
    attempt = _attempt_number(retry_context)
    if attempt > MAX_GENERATION_ATTEMPTS:
        return SqlGenerationResult(
            success=False,
            explanation="Couldn't generate a valid query after 3 attempts.",
            attempt_number=attempt,
            error_message=(
                "Maximum generation attempts exceeded. "
                "Please rephrase your question or check the schema metadata."
            ),
        )

    bundle = metadata_bundle
    if bundle is None:
        try:
            bundle = build_metadata_bundle(data_source_id)
        except NotFoundError:
            return SqlGenerationResult(
                success=False,
                explanation="Data source not found.",
                attempt_number=attempt,
                error_message=f"Data source {data_source_id} not found.",
            )

    if bundle.data_source_id != data_source_id:
        raise ValueError("metadata_bundle.data_source_id does not match data_source_id.")

    cache = embedding_cache or get_embedding_cache()
    selected_tables, matched_glossary_terms = cache.retrieve_tables(bundle, question)
    selected_examples = cache.retrieve_examples(bundle, question)
    negative_feedback: list[dict[str, str]] = []
    try:
        from flask import has_app_context

        if has_app_context():
            negative_feedback = get_negative_feedback_context(data_source_id, question)
    except Exception:
        negative_feedback = []

    system_prompt = build_system_prompt(bundle.dialect_name)
    user_prompt = build_user_prompt(
        question=question,
        bundle=bundle,
        selected_tables=selected_tables,
        selected_examples=selected_examples,
        matched_glossary_terms=matched_glossary_terms,
        conversation_history=conversation_history or [],
        retry_context=retry_context,
        negative_feedback=negative_feedback,
    )
    return _SqlGenerationContext(
        attempt=attempt,
        matched_glossary_terms=matched_glossary_terms,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


def _result_from_tool_output(
    tool_output: SqlGenerationToolOutput,
    *,
    matched_glossary_terms: list[str],
    attempt: int,
) -> SqlGenerationResult:
    sql = tool_output.sql.strip()
    if not sql:
        return SqlGenerationResult(
            success=False,
            explanation="The model returned an empty SQL query.",
            matched_glossary_terms=matched_glossary_terms,
            attempt_number=attempt,
            error_message="Empty SQL returned by model.",
        )

    return SqlGenerationResult(
        success=True,
        sql=sql,
        explanation=tool_output.explanation,
        tables_used=tool_output.tables_used,
        matched_glossary_terms=matched_glossary_terms,
        chart_hint=tool_output.chart_hint,
        confidence=tool_output.confidence,
        attempt_number=attempt,
    )


def _dialect_rules(dialect_name: str) -> list[str]:
    return DIALECT_RULES.get(dialect_name.lower(), DEFAULT_DIALECT_RULES)


def _format_column(column: MetadataBundleColumn) -> str:
    label = column.display_name or column.name
    parts = [f"  - {column.name} ({column.data_type})"]
    if column.display_name and column.display_name != column.name:
        parts[0] += f' aka "{label}"'
    flags: list[str] = []
    if column.is_primary_key:
        flags.append("PK")
    if not column.is_nullable:
        flags.append("NOT NULL")
    if column.is_pii:
        flags.append("PII")
    if flags:
        parts[0] += f" [{', '.join(flags)}]"
    if column.description:
        parts.append(f"    {column.description}")
    if column.sample_distinct_values:
        samples = ", ".join(column.sample_distinct_values[:5])
        parts.append(f"    sample values: {samples}")
    return "\n".join(parts)


def _object_type_label(object_type: str) -> str:
    labels = {
        "table": "Table",
        "view": "View",
        "function": "Function",
        "procedure": "Procedure",
    }
    return labels.get(object_type, object_type.title())


def _format_table(table: MetadataBundleTable) -> str:
    label = table.display_name or table.table_name
    header = f"{_object_type_label(table.object_type)} {table.qualified_name}"
    if table.display_name:
        header += f' ("{label}")'
    lines = [header]
    if table.description:
        lines.append(f"  Description: {table.description}")
    if table.return_type:
        lines.append(f"  Return type: {table.return_type}")
    if table.definition and table.object_type in {"function", "procedure"}:
        definition = table.definition.strip()
        if len(definition) > 500:
            definition = definition[:500] + "…"
        lines.append(f"  Definition: {definition}")
    if table.row_count_estimate is not None and table.object_type in {"table", "view"}:
        lines.append(f"  Estimated rows: {table.row_count_estimate:,}")
    if table.columns:
        column_label = "Parameters" if table.object_type in {"function", "procedure"} else "Columns"
        lines.append(f"  {column_label}:")
        lines.extend(_format_column(column) for column in table.columns)
    return "\n".join(lines)


def _format_relationship(relationship: MetadataBundleRelationship) -> str:
    return (
        f"- {relationship.source_table}.{relationship.source_column} "
        f"-> {relationship.target_table}.{relationship.target_column} "
        f"({relationship.constraint_name})"
    )


def _format_glossary_term(term: MetadataBundleGlossaryTerm) -> str:
    lines = [f'- "{term.term}": {term.definition}']
    if term.sql_expression:
        lines.append(f"  SQL expression: {term.sql_expression}")
    if term.table_name:
        location = term.table_name
        if term.column_name:
            location += f".{term.column_name}"
        lines.append(f"  Related to: {location}")
    return "\n".join(lines)


def _format_example(example: MetadataBundleExample) -> str:
    lines = [
        f"Question: {example.question}",
        f"SQL: {example.sql}",
    ]
    if example.notes:
        lines.append(f"Notes: {example.notes}")
    return "\n".join(lines)


def _filter_relationships(
    relationships: list[MetadataBundleRelationship],
    selected_tables: list[MetadataBundleTable],
) -> list[MetadataBundleRelationship]:
    qualified_names = {table.qualified_name for table in selected_tables}
    return [
        relationship
        for relationship in relationships
        if relationship.source_table in qualified_names
        and relationship.target_table in qualified_names
    ]


def build_system_prompt(dialect_name: str) -> str:
    rules = _dialect_rules(dialect_name)
    rules_text = "\n".join(f"- {rule}" for rule in rules)
    return f"""You are an expert analytics SQL author.

Generate valid {dialect_name} SQL for read-only analytics queries.

Dialect-specific rules:
{rules_text}

Global rules (always follow):
- Generate SELECT statements only. Never produce INSERT, UPDATE, DELETE, DDL, or multi-statement batches.
- Never use SELECT * — always list columns explicitly.
- Always alias computed/aggregated columns with descriptive names (e.g. SUM(amount) AS total_amount).
- Include a row limit when the question does not imply aggregation to a single scalar row:
  use TOP N for tsql, LIMIT N for postgres/mysql/sqlite (default {DEFAULT_ROW_LIMIT} unless the user specifies otherwise).
- Use only tables, views, functions, and procedures provided in the schema context.
- Views are queryable like tables. Table-valued functions may appear in FROM clauses per dialect rules.
- Scalar functions and stored procedures are reference-only unless the dialect supports calling them in SELECT; prefer table and view sources for row data.
- Apply glossary definitions when relevant business terms appear in the question.
- Prefer explicit JOINs with clear ON clauses; use relationships when available.
- Respond ONLY by calling the submit_sql tool — never return free text."""


def build_user_prompt(
    *,
    question: str,
    bundle: MetadataBundle,
    selected_tables: list[MetadataBundleTable],
    selected_examples: list[MetadataBundleExample],
    matched_glossary_terms: list[str],
    conversation_history: list[dict[str, str]],
    retry_context: dict[str, Any] | None,
    negative_feedback: list[dict[str, str]] | None = None,
) -> str:
    sections: list[str] = []

    if retry_context:
        previous_sql = retry_context.get("previous_sql", "")
        execution_error = retry_context.get("execution_error", "")
        sections.append(
            "The previous query failed during execution. Produce a corrected query.\n"
            f"Previous SQL:\n{previous_sql}\n\n"
            f"Execution error:\n{execution_error}"
        )

    if conversation_history:
        history_lines = []
        for message in conversation_history[-10:]:
            role = message.get("role", "user")
            content = message.get("content", "")
            history_lines.append(f"{role}: {content}")
        sections.append(
            "Conversation history (most recent follow-up context):\n"
            + "\n".join(history_lines)
        )

    sections.append(f"Data source: {bundle.data_source_name}")
    sections.append(f"User question: {question}")

    schema_lines = [_format_table(table) for table in selected_tables]
    if schema_lines:
        sections.append("Schema:\n" + "\n\n".join(schema_lines))

    relevant_relationships = _filter_relationships(bundle.relationships, selected_tables)
    if relevant_relationships:
        rel_lines = [_format_relationship(rel) for rel in relevant_relationships]
        sections.append("Relationships:\n" + "\n".join(rel_lines))

    glossary_terms = bundle.glossary
    if matched_glossary_terms:
        glossary_terms = [
            term for term in bundle.glossary if term.term in matched_glossary_terms
        ]
    if glossary_terms:
        glossary_lines = [_format_glossary_term(term) for term in glossary_terms]
        sections.append("Glossary:\n" + "\n".join(glossary_lines))

    if selected_examples:
        example_blocks = [_format_example(example) for example in selected_examples]
        sections.append(
            "Reference examples (question/SQL pairs):\n\n"
            + "\n\n---\n\n".join(example_blocks)
        )

    if negative_feedback:
        warning_blocks = []
        for item in negative_feedback:
            block = (
                f"Question: {item['question']}\n"
                f"Rejected SQL: {item['sql']}"
            )
            if item.get("comment"):
                block += f"\nUser feedback: {item['comment']}"
            warning_blocks.append(block)
        sections.append(
            "Similar questions previously received negative user feedback. "
            "Avoid repeating these SQL patterns or interpretations:\n\n"
            + "\n\n---\n\n".join(warning_blocks)
        )

    return "\n\n".join(sections)


def generate_sql(
    question: str,
    data_source_id: str,
    conversation_history: list[dict[str, str]] | None = None,
    retry_context: dict[str, Any] | None = None,
    *,
    metadata_bundle: MetadataBundle | None = None,
    claude_client: ClaudeClient | None = None,
    embedding_cache: MetadataEmbeddingCache | None = None,
) -> SqlGenerationResult:
    """Generate SQL for a natural-language question scoped to one data source."""
    prepared = _prepare_sql_generation(
        question,
        data_source_id,
        conversation_history=conversation_history,
        retry_context=retry_context,
        metadata_bundle=metadata_bundle,
        embedding_cache=embedding_cache,
    )
    if isinstance(prepared, SqlGenerationResult):
        return prepared

    client = claude_client or _get_claude_client()
    try:
        tool_output = client.generate_sql_tool_output(
            system_prompt=prepared.system_prompt,
            user_prompt=prepared.user_prompt,
        )
    except Exception as exc:
        return SqlGenerationResult(
            success=False,
            explanation="Failed to generate SQL from the language model.",
            matched_glossary_terms=prepared.matched_glossary_terms,
            attempt_number=prepared.attempt,
            error_message=str(exc),
        )

    return _result_from_tool_output(
        tool_output,
        matched_glossary_terms=prepared.matched_glossary_terms,
        attempt=prepared.attempt,
    )


def stream_generate_sql(
    question: str,
    data_source_id: str,
    conversation_history: list[dict[str, str]] | None = None,
    retry_context: dict[str, Any] | None = None,
    *,
    metadata_bundle: MetadataBundle | None = None,
    claude_client: ClaudeClient | None = None,
    embedding_cache: MetadataEmbeddingCache | None = None,
) -> Iterator[dict[str, Any]]:
    """Stream SQL generation events for the chat UI."""
    yield {"type": "started"}

    try:
        prepared = _prepare_sql_generation(
            question,
            data_source_id,
            conversation_history=conversation_history,
            retry_context=retry_context,
            metadata_bundle=metadata_bundle,
            embedding_cache=embedding_cache,
        )
    except Exception as exc:
        yield {
            "type": "error",
            "code": "sql_generation_failed",
            "message": str(exc),
            "details": {
                "explanation": "Failed to prepare SQL generation context.",
                "attempt_number": 1,
                "matched_glossary_terms": [],
            },
        }
        return

    if isinstance(prepared, SqlGenerationResult):
        yield {
            "type": "error",
            "code": "sql_generation_failed",
            "message": prepared.error_message or prepared.explanation,
            "details": {
                "explanation": prepared.explanation,
                "attempt_number": prepared.attempt_number,
                "matched_glossary_terms": prepared.matched_glossary_terms,
            },
        }
        return

    try:
        client = claude_client or _get_claude_client()
    except Exception as exc:
        yield {
            "type": "error",
            "code": "sql_generation_failed",
            "message": str(exc),
            "details": {
                "explanation": "Failed to initialize the configured language model.",
                "attempt_number": prepared.attempt,
                "matched_glossary_terms": prepared.matched_glossary_terms,
            },
        }
        return

    try:
        for event in stream_sql_generation(
            system_prompt=prepared.system_prompt,
            user_prompt=prepared.user_prompt,
            llm_client=client,
        ):
            if event["type"] != "complete":
                yield event
                continue

            tool_output = SqlGenerationToolOutput.model_validate(event["data"])
            result = _result_from_tool_output(
                tool_output,
                matched_glossary_terms=prepared.matched_glossary_terms,
                attempt=prepared.attempt,
            )
            if not result.success:
                yield {
                    "type": "error",
                    "code": "sql_generation_failed",
                    "message": result.error_message or result.explanation,
                    "details": {
                        "explanation": result.explanation,
                        "attempt_number": result.attempt_number,
                        "matched_glossary_terms": result.matched_glossary_terms,
                    },
                }
                return

            yield {
                "type": "complete",
                "data": {
                    "sql": result.sql,
                    "explanation": result.explanation,
                    "tables_referenced": result.tables_used,
                    "confidence": result.confidence,
                    "chart_hint": result.chart_hint,
                    "attempt_number": result.attempt_number,
                },
            }
    except Exception as exc:
        yield {
            "type": "error",
            "code": "sql_generation_failed",
            "message": str(exc),
            "details": {
                "explanation": "Failed to generate SQL from the language model.",
                "attempt_number": prepared.attempt,
                "matched_glossary_terms": prepared.matched_glossary_terms,
            },
        }
