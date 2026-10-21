"""Department business logic (tenant scoped)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.models import Department
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.services import audit_service


def list_active(db: Session, college_id: int) -> list[Department]:
    """Active departments of a college."""
    stmt = (
        select(Department)
        .where(Department.college_id == college_id, Department.is_active.is_(True))
        .order_by(Department.name)
    )
    return list(db.execute(stmt).scalars())


def get_in_college(db: Session, college_id: int, department_id: int) -> Department:
    """Fetch a department of the college or raise NotFoundError."""
    dept = db.execute(
        select(Department).where(
            Department.id == department_id, Department.college_id == college_id
        )
    ).scalar_one_or_none()
    if dept is None:
        raise NotFoundError("Department not found")
    return dept


def _code_taken(db: Session, college_id: int, code: str, exclude_id: int | None) -> bool:
    stmt = select(Department.id).where(
        Department.college_id == college_id, Department.code == code
    )
    if exclude_id is not None:
        stmt = stmt.where(Department.id != exclude_id)
    return db.execute(stmt).first() is not None


def create(db: Session, college_id: int, actor_id: int, data: DepartmentCreate) -> Department:
    """Create a department; duplicate code in the college -> 409."""
    code = data.code.strip().upper()
    if _code_taken(db, college_id, code, None):
        raise ConflictError("Department code already exists")
    dept = Department(college_id=college_id, name=data.name.strip(), code=code, is_active=True)
    db.add(dept)
    db.flush()
    audit_service.record(
        db,
        "DEPARTMENT_CREATE",
        "department",
        user_id=actor_id,
        college_id=college_id,
        resource_id=dept.id,
    )
    db.commit()
    return dept


def update(
    db: Session, college_id: int, actor_id: int, department_id: int, data: DepartmentUpdate
) -> Department:
    """Update a department of the caller's college."""
    dept = get_in_college(db, college_id, department_id)
    if data.code is not None:
        code = data.code.strip().upper()
        if _code_taken(db, college_id, code, dept.id):
            raise ConflictError("Department code already exists")
        dept.code = code
    if data.name is not None:
        dept.name = data.name.strip()
    if data.is_active is not None:
        dept.is_active = data.is_active
    audit_service.record(
        db,
        "DEPARTMENT_UPDATE",
        "department",
        user_id=actor_id,
        college_id=college_id,
        resource_id=dept.id,
    )
    db.commit()
    return dept
