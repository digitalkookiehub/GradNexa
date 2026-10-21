import enum
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, CheckConstraint, Enum, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class QuestionDifficulty(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class AssessmentQuestion(Base, TimestampMixin):
    __tablename__ = "assessment_questions"
    __table_args__ = (CheckConstraint("marks >= 0", name="ck_assessment_questions_marks"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    difficulty: Mapped[QuestionDifficulty] = mapped_column(
        Enum(QuestionDifficulty, name="questiondifficulty"),
        default=QuestionDifficulty.MEDIUM,
        server_default=QuestionDifficulty.MEDIUM.value,
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # List of {"id": str, "text": str}
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    # List of option ids that are correct.
    correct_option_ids: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    marks: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("1"), server_default="1", nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
