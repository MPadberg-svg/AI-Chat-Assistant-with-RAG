"""Okapi BM25 keyword index.

Vector search is good at paraphrases but weak on exact tokens such as error
codes, names and part numbers. This module provides the lexical half of a
hybrid retriever: a dependency-free BM25 implementation over the stored chunks.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Mapping

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

DEFAULT_K1 = 1.5
DEFAULT_B = 0.75


def tokenize(text: str) -> list[str]:
    """Split text into lowercase alphanumeric tokens."""
    return _TOKEN_PATTERN.findall(text.lower())


@dataclass
class BM25Index:
    """In-memory BM25 index over a mapping of ``chunk_id -> text``."""

    k1: float = DEFAULT_K1
    b: float = DEFAULT_B
    _postings: dict[str, dict[str, int]] = field(default_factory=dict, repr=False)
    _idf: dict[str, float] = field(default_factory=dict, repr=False)
    _doc_lengths: dict[str, int] = field(default_factory=dict, repr=False)
    _average_length: float = 0.0

    def __init__(
        self,
        documents: Mapping[str, str] | None = None,
        k1: float = DEFAULT_K1,
        b: float = DEFAULT_B,
    ) -> None:
        self.k1 = k1
        self.b = b
        self._postings = {}
        self._idf = {}
        self._doc_lengths = {}
        self._average_length = 0.0
        if documents:
            self._build(documents)

    def _build(self, documents: Mapping[str, str]) -> None:
        """Index the supplied documents."""
        postings: dict[str, dict[str, int]] = defaultdict(dict)
        lengths: dict[str, int] = {}

        for doc_id, text in documents.items():
            tokens = tokenize(text)
            lengths[doc_id] = len(tokens)
            for term, frequency in Counter(tokens).items():
                postings[term][doc_id] = frequency

        self._doc_lengths = lengths
        self._postings = dict(postings)
        total = sum(lengths.values())
        self._average_length = (total / len(lengths)) if lengths else 0.0

        document_count = len(lengths)
        self._idf = {
            term: math.log(1 + (document_count - len(docs) + 0.5) / (len(docs) + 0.5))
            for term, docs in self._postings.items()
        }

    @property
    def size(self) -> int:
        """Number of indexed documents."""
        return len(self._doc_lengths)

    def search(self, query: str, limit: int = 10) -> list[tuple[str, float]]:
        """Return ``(doc_id, score)`` pairs, best first."""
        terms = tokenize(query)
        if not terms or not self._doc_lengths:
            return []

        scores: dict[str, float] = defaultdict(float)
        for term in set(terms):
            postings = self._postings.get(term)
            if not postings:
                continue
            idf = self._idf[term]
            for doc_id, frequency in postings.items():
                length = self._doc_lengths[doc_id]
                normaliser = self.k1 * (
                    1 - self.b + self.b * (length / self._average_length)
                )
                scores[doc_id] += (
                    idf * (frequency * (self.k1 + 1)) / (frequency + normaliser)
                )

        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        return ranked[:limit]


def reciprocal_rank_fusion(
    rankings: Iterable[Iterable[str]], k: int = 60
) -> list[tuple[str, float]]:
    """Fuse ranked id lists with reciprocal rank fusion.

    RRF scores by position rather than by raw value, so retrievers whose scores
    live on different scales (cosine similarity and BM25) can be combined
    without normalisation.
    """
    fused: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            fused[doc_id] += 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda item: (-item[1], item[0]))
