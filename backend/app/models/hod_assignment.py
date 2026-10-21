from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class HodAssignment(Base, TimestampMixin):
    """Scopes a head-of-department user to a department."""

    __tablename__ = "hod_assignments"
    __table_args__ = (
        UniqueConstraint("hod_user_id", "department_id", name="uq_hod_assignments_user_dept"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    hod_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), index=True, nullable=False
    )
