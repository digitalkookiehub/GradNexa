"""Unit tests for the pure RAG chunker."""
import pytest

from app.services.rag_chunker import chunk_text, is_heading

PARA = (
    "Structured query language lets you retrieve rows from relational tables using joins "
    "filters and aggregates which every placement candidate should practise regularly."
)


def _doc(paragraphs: int = 12) -> str:
    parts = ["# Intro", PARA]
    for i in range(paragraphs):
        parts.append(f"SECTION {i}")
        parts.append((PARA + " ") * 2 + f"Marker{i}.")
    return "\n\n".join(parts)


def test_blank_input_gives_no_chunks() -> None:
    assert chunk_text("") == []
    assert chunk_text("  \n\n \n") == []


def test_tiny_input_single_chunk() -> None:
    chunks = chunk_text("Hello world")
    assert len(chunks) == 1
    assert chunks[0].content == "Hello world"
    assert (chunks[0].char_start, chunks[0].char_end) == (0, 11)
    assert chunks[0].index == 0


def test_offsets_index_back_exactly_and_sizes_bounded() -> None:
    text = _doc()
    chunks = chunk_text(text, 400, 60)
    assert len(chunks) > 3
    for i, c in enumerate(chunks):
        assert c.index == i
        assert text[c.char_start:c.char_end] == c.content
        assert len(c.content) <= 400
        assert c.content == c.content.strip()


def test_no_mid_word_cuts_even_for_huge_unbroken_paragraph() -> None:
    text = " ".join(f"word{i}" for i in range(3000))
    chunks = chunk_text(text, 300, 50)
    words = set(text.split())
    for c in chunks:
        assert text[c.char_start:c.char_end] == c.content
        assert all(w in words for w in c.content.split())
        assert len(c.content) <= 300


def test_long_token_without_spaces_is_still_chunked() -> None:
    text = "x" * 1000
    chunks = chunk_text(text, 300, 50)
    assert len(chunks) >= 4
    assert all(text[c.char_start:c.char_end] == c.content for c in chunks)


def test_overlap_between_consecutive_chunks() -> None:
    text = _doc()
    chunks = chunk_text(text, 400, 100)
    overlaps = [a.char_end - b.char_start for a, b in zip(chunks, chunks[1:], strict=False)]
    assert any(o > 0 for o in overlaps)
    assert all(o <= 100 for o in overlaps)
    assert chunks[0].char_start == 0
    assert chunks[-1].char_end == len(text.rstrip())


def test_zero_overlap_chunks_do_not_overlap() -> None:
    text = _doc()
    chunks = chunk_text(text, 400, 0)
    assert all(a.char_end <= b.char_start for a, b in zip(chunks, chunks[1:], strict=False))


def test_headings_recorded() -> None:
    text = "# Overview\n\nFirst para text here.\n\nSECTION TWO\n\nSecond para text here."
    chunks = chunk_text(text, 60, 0)
    headings = [c.heading for c in chunks]
    assert headings[0] == "Overview"
    assert "SECTION TWO" in headings
    assert chunk_text("No heading at all here.")[0].heading is None


def test_deterministic() -> None:
    text = _doc()
    assert chunk_text(text, 350, 70) == chunk_text(text, 350, 70)


def test_covers_all_text() -> None:
    text = _doc()
    chunks = chunk_text(text, 400, 60)
    covered = set()
    for c in chunks:
        covered.update(range(c.char_start, c.char_end))
    missing = [i for i, ch in enumerate(text) if not ch.isspace() and i not in covered]
    assert not missing


def test_heading_heuristic() -> None:
    assert is_heading("## Joins")
    assert is_heading("PLACEMENT POLICY")
    assert is_heading("2.1 Eligibility Criteria")
    assert not is_heading("This is a normal sentence.")
    assert not is_heading("")
    assert not is_heading("A" * 200)


def test_invalid_chunk_size_rejected() -> None:
    with pytest.raises(ValueError):
        chunk_text("abc", 10, 0)
