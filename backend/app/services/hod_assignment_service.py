"""HOD-to-department assignment logic (tenant scoped)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.models import Department, HodAssignment, User, UserRole
from app.schemas.hod_assignment import HodAssignmentOut
from app.services import audit_service


def list_assignments(db: Session, college_id: int) -> list[HodAssignmentOut]:
    """All HOD assignments of the college with HOD and department names (one query)."""
    rows = db.execute(
        select(
            HodAssignment.id, HodAssignment.hod_user_id, User.full_name, User.email,
            HodAssignment.department_id, Department.name,
        )
        .join(User, User.id == HodAssignment.hod_user_id)
        .join(Department, Department.id == HodAssignment.department_id)
        .where(
            HodAssignment.college_id == college_id,
            User.college_id == college_id,
            Department.college_id == college_id,
        )
        .order_by(HodAssignment.id)
    ).all()
    return [
        HodAssignmentOut(
            id=int(i), hod_user_id=int(u), hod_name=str(n), hod_email=str(e),
            department_id=int(d), department_name=str(dn),
        )
        for i, u, n, e, d, dn in rows
    ]


def create(
    db: Session, college_id: int, actor_id: int, hod_user_id: int, department_id: int
) -> HodAssignmentOut:
    """Assign a HOD user to a department; both must belong to the college."""
    hod = db.execute(
        select(User).where(
            User.id == hod_user_id, User.college_id == college_id, User.role == UserRole.HOD
        )
    ).scalar_one_or_none()
    if hod is None:
        raise NotFoundError("HOD user not found")
    dept = db.execute(
        select(Department).where(
            Department.id == department_id, Department.college_id == college_id
        )
    ).scalar_one_or_none()
    if dept is None:
        raise NotFoundError("Department not found")
    existing = db.execute(
        select(HodAssignment.id).where(
            HodAssignment.college_id == college_id,
            HodAssignment.hod_user_id == hod_user_id,
            HodAssignment.department_id == department_id,
        )
    ).first()
    if existing is not None:
        raise ConflictError("Assignment already exists")
    row = HodAssignment(
        college_id=college_id, hod_user_id=hod_user_id, department_id=department_id
    )
    db.add(row)
    db.flush()
    audit_service.record(
        db, "HOD_ASSIGNMENT_CREATE", "hod_assignment", user_id=actor_id,
        college_id=college_id, resource_id=row.id,
        metadata={"hod_user_id": hod_user_id, "department_id": department_id},
    )
    db.commit()
    return HodAssignmentOut(
        id=row.id, hod_user_id=hod.id, hod_name=hod.full_name, hod_email=hod.email,
        department_id=dept.id, department_name=dept.name,
    )


def delete(db: Session, college_id: int, actor_id: int, assignment_id: int) -> None:
    """Remove an assignment of the college."""
    row = db.execute(
        select(HodAssignment).where(
            HodAssignment.id == assignment_id, HodAssignment.college_id == college_id
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Assignment not found")
    db.delete(row)
    audit_service.record(
        db, "HOD_ASSIGNMENT_DELETE", "hod_assignment", user_id=actor_id,
        college_id=college_id, resource_id=assignment_id,
    )
    db.commit()
