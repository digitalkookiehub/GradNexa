"""Deterministic text chunker for the RAG knowledge base (pure: no I/O, no DB).

Splits text into paragraphs (blank lines / headings), packs them into chunks of about
``chunk_chars`` characters with ``overlap_chars`` of trailing context repeated at the start of the
next chunk, and never cuts inside a word. ``char_start``/``char_end`` index into the input text
exactly: ``text[char_start:char_end] == content``.

The defaults (RAG_CHUNK_CHARS=900, RAG_CHUNK_OVERLAP_CHARS=120) are UNCONFIRMED tuning
assumptions, not validated against a real corpus.
"""
import re
from dataclasses import dataclass

_HEADING_MD = re.compile(r"^\s{0,3}#{1,6}\s+\S")
_NUMBERED = re.compile(r"^\d{1,2}(\.\d{1,2})*[.)]?\s+[A-Z]")


@dataclass(frozen=True)
class Chunk:
    """One chunk with exact offsets into the source text."""

    index: int
    content: str
    char_start: int
    char_end: int
    heading: str | None


@dataclass(frozen=True)
class _Para:
    start: int
    end: int
    heading: str | None  # nearest heading at/above this paragraph
    is_heading: bool


def is_heading(line: str) -> bool:
    """Heuristic: markdown '#', short numbered titles, or short ALL-CAPS / title-like lines."""
    s = line.strip()
    if not s or len(s) > 80:
        return False
    if _HEADING_MD.match(s):
        return True
    if s.endswith((".", ",", ";")):
        return False
    letters = [c for c in s if c.isalpha()]
    if len(letters) >= 3 and s.upper() == s:
        return True
    return bool(_NUMBERED.match(s)) and len(s.split()) <= 8


def _clean_heading(line: str) -> str:
    return line.strip().lstrip("#").strip()


def _paragraphs(text: str) -> list[_Para]:
    """Split on blank lines; a heading line becomes its own paragraph."""
    paras: list[_Para] = []
    heading: str | None = None
    pos = 0
    block_start: int | None = None
    block_end = 0

    def flush() -> None:
        nonlocal block_start
        if block_start is not None:
            paras.append(_Para(block_start, block_end, heading, False))
            block_start = None

    for raw in text.splitlines(keepends=True):
        line = raw.rstrip("\r\n")
        start, end = pos, pos + len(line)
        pos += len(raw)
        if not line.strip():
            flush()
            continue
        if is_heading(line):
            flush()
            heading = _clean_heading(line)
            paras.append(_Para(start, end, heading, True))
            continue
        if block_start is None:
            block_start = start
        block_end = end
    flush()
    return paras


def _word_cut(text: str, lo: int, hi: int) -> int:
    """Largest cut <= hi (and > lo) that falls on whitespace; hi itself if none."""
    if hi >= len(text) or text[hi].isspace():
        return hi
    cut = hi
    while cut > lo and not text[cut - 1].isspace():
        cut -= 1
    return cut if cut > lo else hi


def _word_start(text: str, pos: int, hi: int) -> int:
    """Move pos forward to the next word start so a chunk never begins mid-word."""
    if pos <= 0:
        return 0
    if text[pos - 1].isspace():
        return pos
    while pos < hi and not text[pos].isspace():
        pos += 1
    while pos < hi and text[pos].isspace():
        pos += 1
    return pos


def _trim(text: str, lo: int, hi: int) -> tuple[int, int]:
    while lo < hi and text[lo].isspace():
        lo += 1
    while hi > lo and text[hi - 1].isspace():
        hi -= 1
    return lo, hi


def chunk_text(text: str, chunk_chars: int = 900, overlap_chars: int = 120) -> list[Chunk]:
    """Chunk ``text``. Deterministic; returns [] for blank input."""
    if chunk_chars < 50:
        raise ValueError("chunk_chars must be at least 50")
    overlap = max(0, min(overlap_chars, chunk_chars // 2))
    paras = [p for p in _paragraphs(text) if text[p.start:p.end].strip()]
    if not paras:
        return []

    # Pieces: paragraphs longer than chunk_chars are cut at word boundaries.
    pieces: list[tuple[int, int, str | None]] = []
    for p in paras:
        lo = p.start
        while p.end - lo > chunk_chars:
            cut = _word_cut(text, lo, lo + chunk_chars)
            a, b = _trim(text, lo, cut)
            if b > a:
                pieces.append((a, b, p.heading))
            lo = cut
        a, b = _trim(text, lo, p.end)
        if b > a:
            pieces.append((a, b, p.heading))

    spans: list[tuple[int, int, str | None]] = []
    cur_start: int | None = None
    cur_end = 0
    cur_heading: str | None = None
    for a, b, h in pieces:
        if cur_start is None:
            cur_start, cur_end, cur_heading = a, b, h
        elif b - cur_start <= chunk_chars:
            cur_end = b
        else:
            spans.append((cur_start, cur_end, cur_heading))
            start = a
            if overlap:
                lo = max(0, cur_end - overlap, b - chunk_chars)
                ov = _word_start(text, lo, cur_end)
                if ov < min(a, cur_end):
                    start = ov
            cur_start, cur_end, cur_heading = start, b, h
    if cur_start is not None:
        spans.append((cur_start, cur_end, cur_heading))

    return [
        Chunk(i, text[s:e], s, e, h) for i, (s, e, h) in enumerate(spans)
    ]
