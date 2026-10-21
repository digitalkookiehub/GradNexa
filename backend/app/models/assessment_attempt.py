import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AttemptStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    EXPIRED = "EXPIRED"


class AssessmentAttempt(Base, TimestampMixin):
    __tablename__ = "assessment_attempts"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id", "student_id", "attempt_no", name="uq_assessment_attempts_no"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AttemptStatus] = mapped_column(
        Enum(AttemptStatus, name="attemptstatus"),
        default=AttemptStatus.IN_PROGRESS,
        server_default=AttemptStatus.IN_PROGRESS.value,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # {question_id: [option_ids]}
    answers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
