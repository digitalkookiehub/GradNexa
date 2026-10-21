"""Faculty dashboard endpoint (assigned students only)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.faculty_dashboard import FacultyDashboardResponse
from app.services import faculty_dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/faculty", response_model=FacultyDashboardResponse)
async def faculty_dashboard(
    user: User = Depends(require_role(UserRole.FACULTY)), db: Session = Depends(get_db)
) -> FacultyDashboardResponse:
    """Readiness overview of the caller's assigned students."""
    return faculty_dashboard_service.build(db, user)
