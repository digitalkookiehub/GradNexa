import enum
from typing import Optional

from sqlalchemy import Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SkillScope(str, enum.Enum):
    COMMON = "COMMON"
    DEPARTMENT = "DEPARTMENT"


class SkillCategory(Base, TimestampMixin):
    __tablename__ = "skill_categories"
    __table_args__ = (
        UniqueConstraint("college_id", "name", name="uq_skill_categories_college_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    scope: Mapped[SkillScope] = mapped_column(
        Enum(SkillScope, name="skillscope"),
        default=SkillScope.COMMON,
        server_default=SkillScope.COMMON.value,
        nullable=False,
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), index=True, nullable=True
    )
