"""Embedding cache and similarity retrieval for metadata bundles."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from app.schemas.metadata_bundle import (
    MetadataBundle,
    MetadataBundleExample,
    MetadataBundleGlossaryTerm,
    MetadataBundleTable,
)

TABLE_COUNT_THRESHOLD = 15
TOP_N_TABLES = 10
TOP_N_EXAMPLES = 10

_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _embed(text: str, *, dimensions: int = 256) -> list[float]:
    """Deterministic bag-of-words hash embedding (no external API)."""
    vector = [0.0] * dimensions
    tokens = _tokenize(text)
    if not tokens:
        return vector
    for token in tokens:
        index = hash(token) % dimensions
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def _table_document(table: MetadataBundleTable) -> str:
    parts = [
        table.object_type,
        table.qualified_name,
        table.table_name,
        table.display_name or "",
        table.description or "",
        table.return_type or "",
        (table.definition or "")[:200],
    ]
    for column in table.columns:
        parts.extend(
            [
                column.name,
                column.display_name or "",
                column.description or "",
                column.data_type,
            ]
        )
    return " ".join(part for part in parts if part)


def _question_words(question: str) -> set[str]:
    return set(_tokenize(question))


def _glossary_matches_question(
    term: MetadataBundleGlossaryTerm,
    question_words: set[str],
) -> bool:
    term_words = _tokenize(term.term)
    if not term_words:
        return False
    if all(word in question_words for word in term_words):
        return True
    normalized_term = " ".join(term_words)
    normalized_question = " ".join(sorted(question_words))
    return normalized_term in normalized_question


@dataclass
class _CachedSourceEmbeddings:
    bundle_version: str
    table_embeddings: dict[str, list[float]]
    example_embeddings: dict[str, list[float]]


class MetadataEmbeddingCache:
    """Caches table/example embeddings per data source."""

    def __init__(self) -> None:
        self._cache: dict[str, _CachedSourceEmbeddings] = {}

    def invalidate(self, data_source_id: str) -> None:
        self._cache.pop(data_source_id, None)

    def clear(self) -> None:
        self._cache.clear()

    @staticmethod
    def _bundle_version(bundle: MetadataBundle) -> str:
        table_ids = ",".join(sorted(table.id for table in bundle.tables))
        example_ids = ",".join(sorted(example.id for example in bundle.examples))
        glossary_ids = ",".join(sorted(term.id for term in bundle.glossary))
        return f"{table_ids}|{example_ids}|{glossary_ids}"

    def _ensure_cached(self, bundle: MetadataBundle) -> _CachedSourceEmbeddings:
        version = self._bundle_version(bundle)
        cached = self._cache.get(bundle.data_source_id)
        if cached is not None and cached.bundle_version == version:
            return cached

        table_embeddings = {
            table.id: _embed(_table_document(table)) for table in bundle.tables
        }
        example_embeddings = {
            example.id: _embed(f"{example.question} {example.notes or ''}")
            for example in bundle.examples
        }
        cached = _CachedSourceEmbeddings(
            bundle_version=version,
            table_embeddings=table_embeddings,
            example_embeddings=example_embeddings,
        )
        self._cache[bundle.data_source_id] = cached
        return cached

    def retrieve_tables(
        self,
        bundle: MetadataBundle,
        question: str,
    ) -> tuple[list[MetadataBundleTable], list[str]]:
        """Return relevant tables and matched glossary terms for the question."""
        matched_terms = self.match_glossary_terms(bundle, question)

        if len(bundle.tables) <= TABLE_COUNT_THRESHOLD:
            return bundle.tables, matched_terms

        cached = self._ensure_cached(bundle)
        question_embedding = _embed(question)
        glossary_table_ids = {
            term.table_id
            for term in bundle.glossary
            if term.table_id and _glossary_matches_question(term, _question_words(question))
        }

        scored: list[tuple[float, MetadataBundleTable]] = []
        for table in bundle.tables:
            table_embedding = cached.table_embeddings[table.id]
            score = _cosine(question_embedding, table_embedding)
            scored.append((score, table))

        scored.sort(key=lambda item: item[0], reverse=True)
        selected: dict[str, MetadataBundleTable] = {}

        for table in bundle.tables:
            if table.id in glossary_table_ids:
                selected[table.id] = table

        for _, table in scored:
            if len(selected) >= TOP_N_TABLES:
                break
            selected[table.id] = table

        selected_tables = list(selected.values())
        selected_tables.sort(key=lambda table: table.qualified_name)
        return selected_tables, matched_terms

    def retrieve_examples(
        self,
        bundle: MetadataBundle,
        question: str,
    ) -> list[MetadataBundleExample]:
        if not bundle.examples:
            return []

        cached = self._ensure_cached(bundle)
        question_embedding = _embed(question)
        scored: list[tuple[float, MetadataBundleExample]] = []
        for example in bundle.examples:
            example_embedding = cached.example_embeddings[example.id]
            score = _cosine(question_embedding, example_embedding)
            if example.source == "feedback":
                score += 0.15
            scored.append((score, example))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [example for _, example in scored[:TOP_N_EXAMPLES]]

    @staticmethod
    def match_glossary_terms(
        bundle: MetadataBundle,
        question: str,
    ) -> list[str]:
        words = _question_words(question)
        matched = [
            term.term
            for term in bundle.glossary
            if _glossary_matches_question(term, words)
        ]
        return matched


_default_cache = MetadataEmbeddingCache()


def get_embedding_cache() -> MetadataEmbeddingCache:
    return _default_cache
