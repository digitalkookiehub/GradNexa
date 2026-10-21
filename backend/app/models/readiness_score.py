from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ReadinessScore(Base, TimestampMixin):
    __tablename__ = "readiness_scores"
    __table_args__ = (
        Index("ix_readiness_scores_student_role_computed", "student_id", "role_id", "computed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    role_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("career_roles.id", ondelete="SET NULL"), index=True, nullable=True
    )
    rule_id: Mapped[int] = mapped_column(
        ForeignKey("readiness_rules.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    rule_version: Mapped[int] = mapped_column(Integer, nullable=False)
    overall: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    coverage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    category_scores: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    evidence: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
