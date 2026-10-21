from typing import Any, Optional

from sqlalchemy import JSON, Boolean, CheckConstraint, ForeignKey, Integer, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class InterviewQuestion(Base, TimestampMixin):
    __tablename__ = "interview_questions"
    __table_args__ = (CheckConstraint("min_words >= 0", name="ck_interview_questions_min_words"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    role_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("career_roles.id", ondelete="SET NULL"), index=True, nullable=True
    )
    skill_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("skills.id", ondelete="SET NULL"), index=True, nullable=True
    )
    competency: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # [{"concept": str, "keywords": [str], "weight": number}]
    rubric: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    min_words: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
