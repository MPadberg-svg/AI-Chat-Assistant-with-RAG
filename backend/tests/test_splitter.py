"""Tests for the recursive text splitter."""

from __future__ import annotations

import pytest

from app.core.splitter import split_text


def test_empty_text_returns_no_chunks() -> None:
    """Blank input should not produce empty chunks."""
    assert split_text("", chunk_size=100, chunk_overlap=10) == []
    assert split_text("   \n\n  ", chunk_size=100, chunk_overlap=10) == []


def test_short_text_is_single_chunk() -> None:
    """Text under the limit should be returned unchanged."""
    assert split_text("hello world", chunk_size=100, chunk_overlap=10) == [
        "hello world"
    ]


def test_chunks_respect_size_limit() -> None:
    """No chunk may exceed the configured size."""
    text = " ".join(f"word{i}" for i in range(2000))
    chunks = split_text(text, chunk_size=200, chunk_overlap=20)

    assert len(chunks) > 1
    assert all(len(chunk) <= 200 for chunk in chunks)


def test_no_content_is_lost() -> None:
    """Every word of the source should appear somewhere in the output."""
    words = [f"w{i}" for i in range(500)]
    chunks = split_text(" ".join(words), chunk_size=150, chunk_overlap=15)

    combined = " ".join(chunks)
    for word in words:
        assert word in combined


def test_overlap_is_applied() -> None:
    """Consecutive chunks should share trailing/leading context."""
    text = " ".join(f"token{i}" for i in range(400))
    chunks = split_text(text, chunk_size=120, chunk_overlap=30)

    overlaps = 0
    for previous, following in zip(chunks, chunks[1:]):
        if following.split(" ")[0] in previous:
            overlaps += 1
    assert overlaps > 0


def test_long_unbroken_string_is_hard_split() -> None:
    """A single unbroken run must still be split to fit the limit."""
    chunks = split_text("x" * 1000, chunk_size=100, chunk_overlap=10)

    assert all(len(chunk) <= 100 for chunk in chunks)
    assert "".join(chunks).replace("x", "").strip() == ""


def test_crlf_is_normalised() -> None:
    """Windows line endings should be normalised before splitting."""
    chunks = split_text("line one\r\nline two", chunk_size=100, chunk_overlap=0)

    assert chunks == ["line one\nline two"]


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (-1, 0), (100, 100), (100, 150)],
)
def test_invalid_configuration_raises(chunk_size: int, overlap: int) -> None:
    """Invalid chunk configuration should fail loudly, not loop forever."""
    with pytest.raises(ValueError):
        split_text("some text", chunk_size=chunk_size, chunk_overlap=overlap)
