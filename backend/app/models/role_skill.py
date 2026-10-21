from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RoleSkill(Base, TimestampMixin):
    __tablename__ = "role_skills"
    __table_args__ = (
        UniqueConstraint("role_id", "skill_id", name="uq_role_skills_role_skill"),
        CheckConstraint(
            "required_level >= 0 AND required_level <= 100", name="ck_role_skills_required_level"
        ),
        CheckConstraint("weight > 0", name="ck_role_skills_weight"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("career_roles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    required_level: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
