import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class GapStatus(str, enum.Enum):
    READY = "READY"
    GAP = "GAP"
    NO_EVIDENCE = "NO_EVIDENCE"


class GapPriority(str, enum.Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNASSESSED = "UNASSESSED"


class SkillGap(Base, TimestampMixin):
    __tablename__ = "skill_gaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("career_roles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    readiness_score_id: Mapped[int] = mapped_column(
        ForeignKey("readiness_scores.id", ondelete="CASCADE"), index=True, nullable=False
    )
    current: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    required: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    gap: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    status: Mapped[GapStatus] = mapped_column(Enum(GapStatus, name="gapstatus"), nullable=False)
    priority: Mapped[GapPriority] = mapped_column(
        Enum(GapPriority, name="gappriority"), nullable=False
    )
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
