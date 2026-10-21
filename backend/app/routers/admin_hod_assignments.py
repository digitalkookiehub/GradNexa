"""ADMIN management of HOD-to-department assignments."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.hod_assignment import HodAssignmentCreate, HodAssignmentOut
from app.services import hod_assignment_service as svc

router = APIRouter(prefix="/admin/hod-assignments", tags=["admin-hod-assignments"])
AdminUser = Depends(require_role(UserRole.ADMIN))


@router.get("", response_model=list[HodAssignmentOut])
async def list_hod_assignments(
    admin: User = AdminUser, db: Session = Depends(get_db)
) -> list[HodAssignmentOut]:
    """List HOD assignments in the admin's college."""
    return svc.list_assignments(db, admin.college_id)


@router.post("", response_model=HodAssignmentOut, status_code=201)
async def create_hod_assignment(
    payload: HodAssignmentCreate, admin: User = AdminUser, db: Session = Depends(get_db)
) -> HodAssignmentOut:
    """Assign a HOD to a department."""
    return svc.create(db, admin.college_id, admin.id, payload.hod_user_id, payload.department_id)


@router.delete("/{assignment_id}", status_code=204)
async def delete_hod_assignment(
    assignment_id: int, admin: User = AdminUser, db: Session = Depends(get_db)
) -> Response:
    """Remove a HOD assignment."""
    svc.delete(db, admin.college_id, admin.id, assignment_id)
    return Response(status_code=204)
