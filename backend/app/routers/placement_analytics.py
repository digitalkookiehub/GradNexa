"""Extended placement analytics endpoint (aggregates only)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.placement_analytics import PlacementAnalyticsResponse
from app.services import placement_analytics_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/placement/analytics", response_model=PlacementAnalyticsResponse)
async def placement_analytics(
    department_id: int | None = None,
    user: User = Depends(require_role(UserRole.TPO, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> PlacementAnalyticsResponse:
    """Role readiness, company eligibility counts and progress trends; no identifiers."""
    return placement_analytics_service.build(db, user, department_id)
