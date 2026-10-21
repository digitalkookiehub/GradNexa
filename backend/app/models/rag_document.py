import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RagSourceType(str, enum.Enum):
    SYLLABUS = "SYLLABUS"
    CURRICULUM = "CURRICULUM"
    LEARNING_MATERIAL = "LEARNING_MATERIAL"
    PLACEMENT_GUIDE = "PLACEMENT_GUIDE"
    INTERVIEW_GUIDE = "INTERVIEW_GUIDE"
    POLICY = "POLICY"
    OTHER = "OTHER"


class RagDocumentStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"


class RAGDocument(Base, TimestampMixin):
    """An uploaded knowledge-base document.

    Only APPROVED documents may be retrieved; PENDING and ARCHIVED documents must
    never be returned by retrieval.
    """

    __tablename__ = "rag_documents"
    __table_args__ = (
        UniqueConstraint("storage_key", name="uq_rag_documents_storage_key"),
        Index("ix_rag_documents_college_status", "college_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[RagSourceType] = mapped_column(
        Enum(RagSourceType, name="ragsourcetype"), nullable=False
    )
    # None = applies to all departments
    department_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), index=True, nullable=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[RagDocumentStatus] = mapped_column(
        Enum(RagDocumentStatus, name="ragdocumentstatus"),
        default=RagDocumentStatus.PENDING,
        server_default=RagDocumentStatus.PENDING.value,
        nullable=False,
    )
    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    approved_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
