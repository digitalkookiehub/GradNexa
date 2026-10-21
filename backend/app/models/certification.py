from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Certification(Base, TimestampMixin):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    issued_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
