from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AssessmentResult(Base, TimestampMixin):
    __tablename__ = "assessment_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_attempts.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    assessment_version: Mapped[int] = mapped_column(Integer, nullable=False)
    total_score: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    max_score: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    # {skill_id: {"score": ..., "max": ..., "percentage": ...}}
    per_skill_scores: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
