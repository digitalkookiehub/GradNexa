from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class StudentCareerGoal(Base, TimestampMixin):
    __tablename__ = "student_career_goals"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "career_role_id", name="uq_student_career_goals_student_role"
        ),
        CheckConstraint("priority >= 1", name="ck_student_career_goals_priority"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    career_role_id: Mapped[int] = mapped_column(
        ForeignKey("career_roles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
