"""Unit tests for chunking logic."""
from app.services.ai.text_processing import chunk_text


def test_chunk_text_splits_long_text():
    text = "This is a sentence. " * 500
    chunks = chunk_text(text)

    assert len(chunks) > 1
    assert all(isinstance(c, str) and c.strip() for c in chunks)


def test_chunk_text_short_text_single_chunk():
    text = "Just a short sentence."
    chunks = chunk_text(text)

    assert len(chunks) == 1
    assert chunks[0] == text
