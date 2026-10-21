"""ADMIN: user directory and role management."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.admin_users import RoleChange, RoleChangeResult, UserListResponse
from app.services import admin_user_service

router = APIRouter(prefix="/admin/users", tags=["admin-users"])
AdminUser = Depends(require_role(UserRole.ADMIN))


@router.get("", response_model=UserListResponse)
async def list_users(
    search: str | None = Query(default=None, max_length=100),
    role: UserRole | None = None,
    department_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=admin_user_service.MAX_PAGE_SIZE),
    admin: User = AdminUser,
    db: Session = Depends(get_db),
) -> UserListResponse:
    """Users of the admin's college, filtered by name/email/roll number, role and department."""
    return admin_user_service.list_users(
        db,
        admin.college_id,
        search=search,
        role=role,
        department_id=department_id,
        page=page,
        page_size=page_size,
    )


@router.put("/{user_id}/role", response_model=RoleChangeResult)
async def change_role(
    user_id: int,
    payload: RoleChange,
    admin: User = AdminUser,
    db: Session = Depends(get_db),
) -> RoleChangeResult:
    """Change a user's role (not your own, never SUPER_ADMIN); audit-logged."""
    return admin_user_service.change_role(db, admin.college_id, admin, user_id, payload.role)
