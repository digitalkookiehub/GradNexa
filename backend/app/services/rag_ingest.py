"""Knowledge document ingestion: secure validation, text extraction and chunking.

Accepts PDF and DOCX (validated by magic bytes/structure via resume_text) and plain text
(.txt/.md validated as UTF-8 without NUL bytes). OCR is Not implemented in this phase.
"""
from dataclasses import dataclass

from app.config import settings
from app.exceptions import UnprocessableError
from app.services import rag_chunker
from app.services.resume_text import UnsupportedTypeError, parse_upload

NO_TEXT_MESSAGE = "No extractable text found (OCR is not implemented in this phase)"
TEXT_MIME = "text/plain"
MARKDOWN_MIME = "text/markdown"
_UNSUPPORTED = "Only PDF, DOCX, TXT and MD files are accepted"


@dataclass(frozen=True)
class IngestResult:
    """Extracted text and its chunks."""

    content_type: str
    text: str
    chunks: list[rag_chunker.Chunk]


def _normalise(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


def _parse_text(data: bytes, filename: str | None) -> tuple[str, str]:
    if b"\x00" in data:
        raise UnsupportedTypeError(_UNSUPPORTED)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UnsupportedTypeError(_UNSUPPORTED) from exc
    mime = MARKDOWN_MIME if (filename or "").lower().endswith(".md") else TEXT_MIME
    return mime, _normalise(text)


def extract(data: bytes, filename: str | None) -> tuple[str, str]:
    """Return (content_type, normalised text). Raises 415/422 AppErrors."""
    if not data:
        raise UnprocessableError("The uploaded file is empty")
    if data.startswith(b"%PDF-") or data.startswith(b"PK"):
        parsed = parse_upload(data)
        return parsed.content_type, _normalise(parsed.text)
    return _parse_text(data, filename)


def ingest(data: bytes, filename: str | None) -> IngestResult:
    """Validate, extract and chunk. 422 when there is no extractable text."""
    content_type, text = extract(data, filename)
    if not text.strip():
        raise UnprocessableError(NO_TEXT_MESSAGE)
    chunks = rag_chunker.chunk_text(
        text, settings.RAG_CHUNK_CHARS, settings.RAG_CHUNK_OVERLAP_CHARS
    )
    if not chunks:
        raise UnprocessableError(NO_TEXT_MESSAGE)
    return IngestResult(content_type, text, chunks)
