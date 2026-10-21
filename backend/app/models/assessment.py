import enum
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AssessmentType(str, enum.Enum):
    APTITUDE = "APTITUDE"
    TECHNICAL = "TECHNICAL"
    COMMUNICATION = "COMMUNICATION"
    ROLE_SPECIFIC = "ROLE_SPECIFIC"
    DEPARTMENT_SPECIFIC = "DEPARTMENT_SPECIFIC"
    CUSTOM = "CUSTOM"


class AssessmentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class Assessment(Base, TimestampMixin):
    __tablename__ = "assessments"
    __table_args__ = (
        UniqueConstraint("series_key", "version", name="uq_assessments_series_version"),
        CheckConstraint("negative_marking >= 0", name="ck_assessments_negative_marking"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    # Stable identifier shared by every version of the same assessment.
    series_key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[AssessmentType] = mapped_column(
        Enum(AssessmentType, name="assessmenttype"), nullable=False
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), index=True, nullable=True
    )
    time_limit_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # NULL = unlimited attempts.
    max_attempts: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Fraction of a question's marks deducted per wrong answer.
    negative_marking: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), default=Decimal("0"), server_default="0", nullable=False
    )
    status: Mapped[AssessmentStatus] = mapped_column(
        Enum(AssessmentStatus, name="assessmentstatus"),
        default=AssessmentStatus.DRAFT,
        server_default=AssessmentStatus.DRAFT.value,
        nullable=False,
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
