"""Admin user directory and role management (always scoped to the admin's college)."""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models import (
    Department,
    FacultyAssignment,
    HodAssignment,
    Student,
    User,
    UserRole,
)
from app.schemas.admin_users import (
    RoleChangeResult,
    StudentSummary,
    UserListItem,
    UserListResponse,
)
from app.services import audit_service

USER_ROLE_CHANGE = "USER_ROLE_CHANGE"
MAX_PAGE_SIZE = 100


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_users(
    db: Session,
    college_id: int,
    *,
    search: str | None,
    role: UserRole | None,
    department_id: int | None,
    page: int,
    page_size: int,
) -> UserListResponse:
    """A page of the college's users, newest first, with student details when they have any."""
    page = max(page, 1)
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
    conditions = [User.college_id == college_id]
    if role is not None:
        conditions.append(User.role == role)
    if department_id is not None:
        conditions.append(Student.department_id == department_id)
    term = (search or "").strip()
    if term:
        like = f"%{_escape_like(term.lower())}%"
        conditions.append(
            or_(
                func.lower(User.full_name).like(like, escape="\\"),
                func.lower(User.email).like(like, escape="\\"),
                func.lower(func.coalesce(Student.roll_number, "")).like(like, escape="\\"),
            )
        )
    base = (
        select(User, Student, Department.name)
        .outerjoin(Student, (Student.user_id == User.id) & (Student.college_id == college_id))
        .outerjoin(Department, Department.id == Student.department_id)
        .where(*conditions)
    )
    total = db.execute(
        select(func.count())
        .select_from(User)
        .outerjoin(Student, (Student.user_id == User.id) & (Student.college_id == college_id))
        .where(*conditions)
    ).scalar_one()
    rows = db.execute(
        base.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = [
        UserListItem(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            student=None
            if student is None
            else StudentSummary(
                student_id=student.id,
                department_id=student.department_id,
                department_name=dept_name,
                roll_number=student.roll_number,
                graduation_year=student.graduation_year,
                profile_complete=bool(
                    student.department_id and student.roll_number and student.graduation_year
                ),
            ),
        )
        for user, student, dept_name in rows
    ]
    return UserListResponse(items=items, total=total, page=page, page_size=page_size)


def change_role(
    db: Session, college_id: int, actor: User, user_id: int, new_role: UserRole
) -> RoleChangeResult:
    """Change a user's role within the admin's college.

    Rules: not yourself; never a SUPER_ADMIN account; leaving FACULTY or HOD removes that
    user's faculty / HOD assignments so no stale access remains. The role is read from the
    database on every request, so the change applies to the user's existing sessions at once.
    """
    target = db.execute(
        select(User).where(User.id == user_id, User.college_id == college_id)
    ).scalar_one_or_none()
    if target is None:
        raise NotFoundError("User not found")
    if target.id == actor.id:
        raise ConflictError("You cannot change your own role")
    if target.role == UserRole.SUPER_ADMIN:
        raise ForbiddenError("This account's role cannot be changed here")
    previous = target.role
    removed_faculty = 0
    removed_hod = 0
    if previous != new_role:
        if previous == UserRole.FACULTY:
            rows = db.execute(
                select(FacultyAssignment).where(
                    FacultyAssignment.college_id == college_id,
                    FacultyAssignment.faculty_user_id == target.id,
                )
            ).scalars().all()
            removed_faculty = len(rows)
            for row in rows:
                db.delete(row)
        if previous == UserRole.HOD:
            hod_rows = db.execute(
                select(HodAssignment).where(
                    HodAssignment.college_id == college_id,
                    HodAssignment.hod_user_id == target.id,
                )
            ).scalars().all()
            removed_hod = len(hod_rows)
            for hod_row in hod_rows:
                db.delete(hod_row)
        target.role = new_role
        audit_service.record(
            db,
            USER_ROLE_CHANGE,
            "user",
            user_id=actor.id,
            college_id=college_id,
            resource_id=target.id,
            metadata={
                "from": previous.value,
                "to": new_role.value,
                "removed_faculty_assignments": removed_faculty,
                "removed_hod_assignments": removed_hod,
            },
        )
        db.commit()
    return RoleChangeResult(
        id=target.id,
        role=target.role,
        previous_role=previous,
        removed_faculty_assignments=removed_faculty,
        removed_hod_assignments=removed_hod,
    )
