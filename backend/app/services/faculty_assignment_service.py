"""Faculty-to-student assignment logic (tenant scoped)."""
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.exceptions import ConflictError, NotFoundError
from app.models import FacultyAssignment, Student, User, UserRole
from app.schemas.student import FacultyAssignmentDetail
from app.services import audit_service


def list_assignments(db: Session, college_id: int) -> list[FacultyAssignmentDetail]:
    """All assignments in the college, with faculty and student names."""
    faculty = aliased(User)
    student_user = aliased(User)
    stmt = (
        select(FacultyAssignment, faculty, student_user)
        .join(faculty, faculty.id == FacultyAssignment.faculty_user_id)
        .join(Student, Student.id == FacultyAssignment.student_id)
        .join(student_user, student_user.id == Student.user_id)
        .where(FacultyAssignment.college_id == college_id)
        .order_by(FacultyAssignment.id)
    )
    return [
        FacultyAssignmentDetail(
            id=row.id,
            faculty_user_id=f.id,
            faculty_name=f.full_name,
            faculty_email=f.email,
            student_id=row.student_id,
            student_name=s.full_name,
            student_email=s.email,
        )
        for row, f, s in db.execute(stmt).all()
    ]


def create(
    db: Session, college_id: int, actor_id: int, faculty_user_id: int, student_id: int
) -> FacultyAssignment:
    """Assign a student to a FACULTY user; both must belong to the college."""
    faculty = db.execute(
        select(User.id).where(
            User.id == faculty_user_id,
            User.college_id == college_id,
            User.role == UserRole.FACULTY,
        )
    ).first()
    if faculty is None:
        raise NotFoundError("Faculty user not found")
    student = db.execute(
        select(Student.id).where(Student.id == student_id, Student.college_id == college_id)
    ).first()
    if student is None:
        raise NotFoundError("Student not found")
    existing = db.execute(
        select(FacultyAssignment.id).where(
            FacultyAssignment.college_id == college_id,
            FacultyAssignment.faculty_user_id == faculty_user_id,
            FacultyAssignment.student_id == student_id,
        )
    ).first()
    if existing is not None:
        raise ConflictError("Assignment already exists")
    row = FacultyAssignment(
        college_id=college_id, faculty_user_id=faculty_user_id, student_id=student_id
    )
    db.add(row)
    db.flush()
    audit_service.record(
        db,
        "FACULTY_ASSIGNMENT_CREATE",
        "faculty_assignment",
        user_id=actor_id,
        college_id=college_id,
        resource_id=row.id,
        metadata={"faculty_user_id": faculty_user_id, "student_id": student_id},
    )
    db.commit()
    return row


def delete(db: Session, college_id: int, actor_id: int, assignment_id: int) -> None:
    """Remove an assignment of the college."""
    row = db.execute(
        select(FacultyAssignment).where(
            FacultyAssignment.id == assignment_id, FacultyAssignment.college_id == college_id
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Assignment not found")
    db.delete(row)
    audit_service.record(
        db,
        "FACULTY_ASSIGNMENT_DELETE",
        "faculty_assignment",
        user_id=actor_id,
        college_id=college_id,
        resource_id=assignment_id,
    )
    db.commit()
