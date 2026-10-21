"""ADMIN/FACULTY learning resource curation; approval is ADMIN only."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.planning import ResourceAdmin, ResourceCreate, ResourceUpdate
from app.services import learning_resource_service as svc

router = APIRouter(prefix="/admin/learning-resources", tags=["admin-learning-resources"])
Staff = Depends(require_role(UserRole.ADMIN, UserRole.FACULTY))
AdminUser = Depends(require_role(UserRole.ADMIN))


@router.get("", response_model=list[ResourceAdmin])
async def list_resources(
    skill_id: int | None = None,
    approved: bool | None = None,
    user: User = Staff,
    db: Session = Depends(get_db),
) -> list[ResourceAdmin]:
    """All learning resources of the college."""
    return svc.list_admin(db, user.college_id, skill_id, approved)


@router.post("", response_model=ResourceAdmin, status_code=201)
async def create_resource(
    payload: ResourceCreate, user: User = Staff, db: Session = Depends(get_db)
) -> ResourceAdmin:
    """Create an unapproved resource."""
    return svc.to_admin(db, svc.create_resource(db, user, payload))


@router.put("/{resource_id}", response_model=ResourceAdmin)
async def update_resource(
    resource_id: int, payload: ResourceUpdate, user: User = Staff, db: Session = Depends(get_db)
) -> ResourceAdmin:
    """Update a resource; changing url or skill resets approval."""
    return svc.to_admin(db, svc.update_resource(db, user, resource_id, payload))


@router.delete("/{resource_id}", status_code=204)
async def delete_resource(
    resource_id: int, user: User = Staff, db: Session = Depends(get_db)
) -> Response:
    """Delete a resource."""
    svc.delete_resource(db, user, resource_id)
    return Response(status_code=204)


@router.post("/{resource_id}/approve", response_model=ResourceAdmin)
async def approve_resource(
    resource_id: int, user: User = AdminUser, db: Session = Depends(get_db)
) -> ResourceAdmin:
    """Approve a resource for use in student plans."""
    return svc.to_admin(db, svc.set_approval(db, user, resource_id, True))


@router.post("/{resource_id}/unapprove", response_model=ResourceAdmin)
async def unapprove_resource(
    resource_id: int, user: User = AdminUser, db: Session = Depends(get_db)
) -> ResourceAdmin:
    """Withdraw approval of a resource."""
    return svc.to_admin(db, svc.set_approval(db, user, resource_id, False))
