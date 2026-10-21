import enum
from datetime import date
from typing import Optional

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PlanStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class LearningPlan(Base, TimestampMixin):
    __tablename__ = "learning_plans"
    __table_args__ = (
        Index("ix_learning_plans_student_status", "student_id", "status"),
        CheckConstraint("skills_per_week >= 1", name="ck_learning_plans_skills_per_week"),
        CheckConstraint("duration_days >= 1", name="ck_learning_plans_duration_days"),
    )

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
    baseline_readiness_score_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("readiness_scores.id", ondelete="SET NULL"), index=True, nullable=True
    )
    status: Mapped[PlanStatus] = mapped_column(
        Enum(PlanStatus, name="planstatus"),
        default=PlanStatus.ACTIVE,
        server_default=PlanStatus.ACTIVE.value,
        nullable=False,
    )
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    duration_days: Mapped[int] = mapped_column(
        Integer, default=30, server_default="30", nullable=False
    )
    skills_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
