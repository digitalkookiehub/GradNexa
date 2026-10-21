"""Schemas for the RAG knowledge base API."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import RagDocumentStatus, RagSourceType


class DocumentResponse(BaseModel):
    """Knowledge document metadata (no raw file access)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source_type: RagSourceType
    department_id: int | None
    department_name: str | None
    original_filename: str
    content_type: str
    size_bytes: int
    status: RagDocumentStatus
    uploaded_by: int
    approved_by: int | None
    approved_at: datetime | None
    chunk_count: int
    created_at: datetime


class DocumentUpdate(BaseModel):
    """Metadata-only update; an explicit null department_id clears the department."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    source_type: RagSourceType | None = None
    department_id: int | None = None

    @field_validator("title")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("title must not be blank")
        return value.strip() if value else value


class ChunkItem(BaseModel):
    """One stored chunk."""

    id: int
    chunk_index: int
    content: str
    heading: str | None


class ChunkListResponse(BaseModel):
    """Paged chunks of a document."""

    total: int
    chunks: list[ChunkItem]


class SearchRequest(BaseModel):
    """Knowledge search request."""

    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=10)


class PassageResponse(BaseModel):
    """A citable passage: a real stored chunk."""

    document_id: int
    document_title: str
    source_type: str
    chunk_id: int
    chunk_index: int
    snippet: str
    score: float
    query_coverage: float


class SearchResponse(BaseModel):
    """Knowledge search result."""

    query: str
    insufficient_evidence: bool
    message: str | None
    passages: list[PassageResponse]
