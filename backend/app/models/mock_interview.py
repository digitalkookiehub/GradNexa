import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class InterviewStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class MockInterview(Base, TimestampMixin):
    __tablename__ = "mock_interviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("career_roles.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus, name="interviewstatus"),
        default=InterviewStatus.IN_PROGRESS,
        server_default=InterviewStatus.IN_PROGRESS.value,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
