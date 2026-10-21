from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class InterviewResult(Base, TimestampMixin):
    __tablename__ = "interview_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interview_id: Mapped[int] = mapped_column(
        ForeignKey("mock_interviews.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("career_roles.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    overall: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    competency_scores: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    per_question: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(50), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
