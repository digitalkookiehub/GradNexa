import enum
from decimal import Decimal
from typing import Optional

from sqlalchemy import JSON, CheckConstraint, Enum, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CgpaBasis(str, enum.Enum):
    LATEST_SEMESTER = "LATEST_SEMESTER"
    AVERAGE_ALL_SEMESTERS = "AVERAGE_ALL_SEMESTERS"


class EligibilityRule(Base, TimestampMixin):
    """Hard eligibility criteria for a job (one rule set per job).

    Eligibility is separate from readiness: it is a pass/fail gate on institutional
    criteria and never feeds the readiness score.
    """

    __tablename__ = "eligibility_rules"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_eligibility_rules_job_id"),
        CheckConstraint(
            "cgpa_min IS NULL OR (cgpa_min >= 0 AND cgpa_min <= 10)",
            name="ck_eligibility_rules_cgpa_min",
        ),
        CheckConstraint(
            "max_arrears IS NULL OR max_arrears >= 0", name="ck_eligibility_rules_max_arrears"
        ),
        CheckConstraint(
            "attendance_min IS NULL OR (attendance_min >= 0 AND attendance_min <= 100)",
            name="ck_eligibility_rules_attendance_min",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False
    )
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    cgpa_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2), nullable=True)
    # Intentionally NOT defaulted: which CGPA to compare is institutional policy and
    # must be chosen explicitly by the college when cgpa_min is set.
    cgpa_basis: Mapped[Optional[CgpaBasis]] = mapped_column(
        Enum(CgpaBasis, name="cgpabasis"), nullable=True
    )
    max_arrears: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    attendance_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    # list[int]; None = all departments
    department_ids: Mapped[Optional[list[int]]] = mapped_column(JSON, nullable=True)
    # list[int]; None = all graduation years
    graduation_years: Mapped[Optional[list[int]]] = mapped_column(JSON, nullable=True)
    # list[str]; informational only, never evaluated automatically
    custom_notes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
