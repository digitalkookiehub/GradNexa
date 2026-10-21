"""Schemas for the admin Users and students screen."""
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models import UserRole

ASSIGNABLE_ROLES = (
    UserRole.STUDENT,
    UserRole.FACULTY,
    UserRole.TPO,
    UserRole.HOD,
    UserRole.ADMIN,
)


class StudentSummary(BaseModel):
    """Student-specific columns shown next to a STUDENT user."""

    student_id: int
    department_id: int | None
    department_name: str | None
    roll_number: str | None
    graduation_year: int | None
    profile_complete: bool


class UserListItem(BaseModel):
    """One user in the college."""

    id: int
    full_name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    student: StudentSummary | None


class UserListResponse(BaseModel):
    """A page of users plus the total that matched the filters."""

    items: list[UserListItem]
    total: int
    page: int
    page_size: int


class RoleChange(BaseModel):
    """Request to change a user's role."""

    role: UserRole

    @field_validator("role")
    @classmethod
    def must_be_assignable(cls, value: UserRole) -> UserRole:
        """SUPER_ADMIN is never assignable from the college admin screen."""
        if value not in ASSIGNABLE_ROLES:
            raise ValueError("Role cannot be assigned here")
        return value


class RoleChangeResult(BaseModel):
    """Outcome of a role change."""

    id: int
    role: UserRole
    previous_role: UserRole
    removed_faculty_assignments: int
    removed_hod_assignments: int
