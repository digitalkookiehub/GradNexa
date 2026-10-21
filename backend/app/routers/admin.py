"""ADMIN endpoints: departments and faculty assignments."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import Department, FacultyAssignment, User, UserRole
from app.schemas.department import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.schemas.student import (
    FacultyAssignmentCreate,
    FacultyAssignmentDetail,
    FacultyAssignmentResponse,
)
from app.services import department_service, faculty_assignment_service

router = APIRouter(prefix="/admin", tags=["admin"])
AdminUser = Depends(require_role(UserRole.ADMIN))


@router.post("/departments", response_model=DepartmentResponse, status_code=201)
async def create_department(
    payload: DepartmentCreate, admin: User = AdminUser, db: Session = Depends(get_db)
) -> Department:
    """Create a department in the admin's college."""
    return department_service.create(db, admin.college_id, admin.id, payload)


@router.put("/departments/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    admin: User = AdminUser,
    db: Session = Depends(get_db),
) -> Department:
    """Update a department of the admin's college."""
    return department_service.update(db, admin.college_id, admin.id, department_id, payload)


@router.get("/faculty-assignments", response_model=list[FacultyAssignmentDetail])
async def list_assignments(
    admin: User = AdminUser, db: Session = Depends(get_db)
) -> list[FacultyAssignmentDetail]:
    """List faculty assignments in the admin's college."""
    return faculty_assignment_service.list_assignments(db, admin.college_id)


@router.post("/faculty-assignments", response_model=FacultyAssignmentResponse, status_code=201)
async def create_assignment(
    payload: FacultyAssignmentCreate, admin: User = AdminUser, db: Session = Depends(get_db)
) -> FacultyAssignment:
    """Assign a student to a faculty user."""
    return faculty_assignment_service.create(
        db, admin.college_id, admin.id, payload.faculty_user_id, payload.student_id
    )


@router.delete("/faculty-assignments/{assignment_id}", status_code=204)
async def delete_assignment(
    assignment_id: int, admin: User = AdminUser, db: Session = Depends(get_db)
) -> Response:
    """Remove a faculty assignment."""
    faculty_assignment_service.delete(db, admin.college_id, admin.id, assignment_id)
    return Response(status_code=204)
