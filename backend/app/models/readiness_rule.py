from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ReadinessRule(Base, TimestampMixin):
    """Per-college readiness scoring rules.

    Rules are immutable once created; changes create a new version.
    No default weights/thresholds exist anywhere: they are institutional policy
    and must be supplied explicitly by the college.
    """

    __tablename__ = "readiness_rules"
    __table_args__ = (
        UniqueConstraint("college_id", "version", name="uq_readiness_rules_college_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    # {skill_category_id (str): weight number}
    weights: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # [{"level": str, "min_score": number}]
    level_thresholds: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    # {"high_min_gap": number, "medium_min_gap": number}
    gap_thresholds: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
