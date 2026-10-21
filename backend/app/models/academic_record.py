from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AcademicRecord(Base, TimestampMixin):
    __tablename__ = "academic_records"
    __table_args__ = (
        UniqueConstraint("student_id", "semester", name="uq_academic_records_student_sem"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    cgpa: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    active_arrears: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    attendance_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
