"""Student dashboard endpoint (STUDENT only, own data)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.student_dashboard import StudentDashboardResponse
from app.services import student_dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/student", response_model=StudentDashboardResponse)
async def student_dashboard(
    user: User = Depends(require_role(UserRole.STUDENT)), db: Session = Depends(get_db)
) -> StudentDashboardResponse:
    """The caller's dashboard built from stored data only."""
    return student_dashboard_service.build(db, user)
