"""Recursive character text splitter.

Replaces ``langchain-text-splitters``. Splits text on progressively finer
separators (paragraph, line, sentence, word, character) and then merges the
resulting pieces back into chunks of at most ``chunk_size`` characters with
``chunk_overlap`` characters of context carried over between chunks.
"""

from __future__ import annotations

from typing import Iterable, Sequence

DEFAULT_SEPARATORS: tuple[str, ...] = ("\n\n", "\n", ". ", " ", "")


def split_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    separators: Sequence[str] = DEFAULT_SEPARATORS,
) -> list[str]:
    """Split ``text`` into overlapping chunks.

    Args:
        text: Input text. CRLF line endings are normalised first.
        chunk_size: Maximum chunk length in characters.
        chunk_overlap: Characters of context repeated at the start of a chunk.
        separators: Ordered separators, finest last (``""`` splits by character).

    Returns:
        A list of non-empty, stripped chunks.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must not be negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    normalised = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalised:
        return []

    pieces = _split_recursive(normalised, tuple(separators), chunk_size)
    return _merge_pieces(pieces, chunk_size, chunk_overlap)


def _split_recursive(
    text: str, separators: tuple[str, ...], chunk_size: int
) -> list[str]:
    """Split ``text`` using the coarsest separator that occurs in it."""
    if len(text) <= chunk_size:
        return [text]

    separator = separators[-1]
    remaining: tuple[str, ...] = ()
    for index, candidate in enumerate(separators):
        if candidate == "":
            separator = candidate
            break
        if candidate in text:
            separator = candidate
            remaining = separators[index + 1 :]
            break

    if separator == "":
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    splits = text.split(separator)
    pieces: list[str] = []
    for index, part in enumerate(splits):
        # Keep the separator attached so no characters are lost.
        piece = part + (separator if index < len(splits) - 1 else "")
        if not piece:
            continue
        if len(piece) > chunk_size:
            pieces.extend(_split_recursive(piece, remaining or ("",), chunk_size))
        else:
            pieces.append(piece)
    return pieces


def _merge_pieces(
    pieces: Iterable[str], chunk_size: int, chunk_overlap: int
) -> list[str]:
    """Greedily merge pieces into overlapping chunks."""
    chunks: list[str] = []
    current: list[str] = []
    total = 0

    for piece in pieces:
        if not piece:
            continue
        length = len(piece)
        if total + length > chunk_size:
            if current:
                chunk = "".join(current).strip()
                if chunk:
                    chunks.append(chunk)
                # Drop leading pieces until we are under the overlap budget.
                while current and (
                    total > chunk_overlap or (total + length > chunk_size and total > 0)
                ):
                    total -= len(current[0])
                    current.pop(0)
        current.append(piece)
        total += length

    tail = "".join(current).strip()
    if tail:
        chunks.append(tail)
    return chunks
