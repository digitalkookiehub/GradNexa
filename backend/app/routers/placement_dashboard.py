"""Placement officer dashboard endpoint (aggregates only)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.placement_dashboard import PlacementDashboardResponse
from app.services import placement_dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/placement", response_model=PlacementDashboardResponse)
async def placement_dashboard(
    department_id: int | None = None,
    user: User = Depends(require_role(UserRole.TPO, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> PlacementDashboardResponse:
    """College-wide (or one department) readiness aggregates; no student identifiers."""
    return placement_dashboard_service.build(db, user, department_id)
