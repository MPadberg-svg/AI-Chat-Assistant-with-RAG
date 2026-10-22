"""Tests for the BM25 index and rank fusion."""

from __future__ import annotations

from app.core.bm25 import BM25Index, reciprocal_rank_fusion, tokenize


def test_tokenize_lowercases_and_splits() -> None:
    assert tokenize("Deploy-42_failed!") == ["deploy", "42", "failed"]


def test_tokenize_empty() -> None:
    assert tokenize("   ") == []


def test_empty_index_returns_nothing() -> None:
    assert BM25Index({}).search("anything") == []


def test_empty_query_returns_nothing() -> None:
    index = BM25Index({"a": "hello world"})
    assert index.search("") == []


def test_exact_term_match_outranks_unrelated_text() -> None:
    """BM25 exists to catch exact tokens that embeddings blur."""
    index = BM25Index(
        {
            "match": "Restart the service when ERR_CONN_REFUSED appears.",
            "other": "A long unrelated paragraph about billing and invoices.",
            "third": "Another unrelated note mentioning deployment windows.",
        }
    )

    results = index.search("ERR_CONN_REFUSED")

    assert results
    assert results[0][0] == "match"


def test_rare_terms_score_higher_than_common_ones() -> None:
    """IDF should reward discriminative terms."""
    index = BM25Index(
        {
            "a": "deployment deployment deployment rollback",
            "b": "deployment general notes",
            "c": "deployment general notes",
        }
    )

    # "rollback" only appears in one document, unlike "deployment".
    assert index.search("rollback")[0][0] == "a"
    assert len(index.search("deployment")) == 3


def test_search_respects_limit() -> None:
    documents = {f"d{index}": f"common token {index}" for index in range(20)}
    results = BM25Index(documents).search("common", limit=3)

    assert len(results) == 3


def test_size_reports_document_count() -> None:
    assert BM25Index({"a": "x", "b": "y"}).size == 2


def test_unknown_terms_are_ignored() -> None:
    index = BM25Index({"a": "known term"})
    assert index.search("zzz-nothing-here") == []


def test_rrf_rewards_documents_found_by_both_retrievers() -> None:
    """A chunk ranked by both lists should beat one ranked by a single list."""
    vector_ranking = ["shared", "vector-only"]
    lexical_ranking = ["shared", "lexical-only"]

    fused = reciprocal_rank_fusion([vector_ranking, lexical_ranking])

    assert fused[0][0] == "shared"


def test_rrf_with_empty_rankings() -> None:
    assert reciprocal_rank_fusion([[], []]) == []


def test_rrf_scores_descend() -> None:
    fused = reciprocal_rank_fusion([["a", "b", "c"]])

    assert [doc_id for doc_id, _ in fused] == ["a", "b", "c"]
    assert fused[0][1] > fused[1][1] > fused[2][1]
