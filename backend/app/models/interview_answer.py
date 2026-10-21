from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class InterviewAnswer(Base, TimestampMixin):
    __tablename__ = "interview_answers"
    __table_args__ = (
        UniqueConstraint(
            "interview_id", "question_id", name="uq_interview_answers_interview_question"
        ),
        CheckConstraint("position >= 1", name="ck_interview_answers_position"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interview_id: Mapped[int] = mapped_column(
        ForeignKey("mock_interviews.id", ondelete="CASCADE"), index=True, nullable=False
    )
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("interview_questions.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    answer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    answered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
