from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RAGChunk(Base, TimestampMixin):
    """A text chunk of a RAGDocument, used for retrieval.

    There is intentionally NO embedding column in this phase (no embedding provider
    is configured yet); a pgvector column is added by a later migration once a
    provider is chosen.
    """

    __tablename__ = "rag_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_rag_chunks_document_chunk"),
        CheckConstraint("chunk_index >= 0", name="ck_rag_chunks_chunk_index"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False
    )
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    # Not named `metadata`: that attribute is reserved by SQLAlchemy declarative.
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
