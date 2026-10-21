"""HOD dashboard endpoint (aggregates only, assigned departments only)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.hod_dashboard import HodDashboardResponse
from app.services import hod_dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/hod", response_model=HodDashboardResponse)
async def hod_dashboard(
    department_id: int | None = None,
    user: User = Depends(require_role(UserRole.HOD)),
    db: Session = Depends(get_db),
) -> HodDashboardResponse:
    """Aggregates for the HOD's assigned department(s); no student identifiers."""
    return hod_dashboard_service.build(db, user, department_id)
