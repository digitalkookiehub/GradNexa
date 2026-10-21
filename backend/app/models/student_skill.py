from decimal import Decimal
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class StudentSkill(Base, TimestampMixin):
    __tablename__ = "student_skills"
    __table_args__ = (
        UniqueConstraint("student_id", "skill_id", name="uq_student_skills_student_skill"),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_student_skills_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    evidence_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    last_result_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("assessment_results.id", ondelete="SET NULL"), index=True, nullable=True
    )
    # Intentionally left NULL until the Phase 3 readiness rules define how
    # confidence is computed; Phase 2 code must not populate it.
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3), nullable=True)
