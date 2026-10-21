import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PlanItemKind(str, enum.Enum):
    LEARN = "LEARN"
    PRACTICE = "PRACTICE"
    ASSESS = "ASSESS"
    REASSESS = "REASSESS"


class PlanItemStatus(str, enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class LearningPlanItem(Base, TimestampMixin):
    __tablename__ = "learning_plan_items"
    __table_args__ = (
        CheckConstraint("week >= 1 AND week <= 4", name="ck_learning_plan_items_week"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("learning_plans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    week: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[PlanItemKind] = mapped_column(
        Enum(PlanItemKind, name="planitemkind"), nullable=False
    )
    skill_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("skills.id", ondelete="SET NULL"), index=True, nullable=True
    )
    resource_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("learning_resources.id", ondelete="SET NULL"), index=True, nullable=True
    )
    task: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[PlanItemStatus] = mapped_column(
        Enum(PlanItemStatus, name="planitemstatus"),
        default=PlanItemStatus.TODO,
        server_default=PlanItemStatus.TODO.value,
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
