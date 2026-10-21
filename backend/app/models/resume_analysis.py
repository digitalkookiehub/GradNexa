from typing import Any, Optional

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ResumeAnalysis(Base, TimestampMixin):
    __tablename__ = "resume_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    role_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("career_roles.id", ondelete="SET NULL"), index=True, nullable=True
    )
    extractor_version: Mapped[str] = mapped_column(String(50), nullable=False)
    extracted: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    role_match: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    jd_match: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    notes: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
