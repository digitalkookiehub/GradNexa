"""Readiness endpoints (student compute/read, staff read) and the career role catalogue."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_role
from app.models import User, UserRole
from app.schemas.planning import StudentCareerRoleDetailResponse, StudentCareerRoleResponse
from app.schemas.readiness import (
    GapResponse,
    ReadinessComputeRequest,
    ReadinessResultResponse,
)
from app.services import (
    career_goal_service,
    career_role_service,
    readiness_service,
    student_service,
)

router = APIRouter(tags=["readiness"])
StudentUser = Depends(require_role(UserRole.STUDENT))


@router.post("/readiness/compute", response_model=ReadinessResultResponse, status_code=201)
async def compute_readiness(
    payload: ReadinessComputeRequest | None = None,
    user: User = StudentUser,
    db: Session = Depends(get_db),
) -> ReadinessResultResponse:
    """Compute and store the caller's readiness (general, or for a role)."""
    student = student_service.get_or_create_me(db, user)
    role_id = payload.role_id if payload is not None else None
    return readiness_service.compute(db, user, student, role_id)


@router.get("/readiness/me", response_model=ReadinessResultResponse)
async def my_readiness(
    role_id: int | None = None, user: User = StudentUser, db: Session = Depends(get_db)
) -> ReadinessResultResponse:
    """Latest stored readiness result of the caller."""
    student = student_service.get_or_create_me(db, user)
    return readiness_service.latest_result(db, student, role_id)


@router.get("/readiness/me/history", response_model=list[ReadinessResultResponse])
async def my_readiness_history(
    role_id: int | None = None, user: User = StudentUser, db: Session = Depends(get_db)
) -> list[ReadinessResultResponse]:
    """Stored readiness results of the caller, newest first."""
    student = student_service.get_or_create_me(db, user)
    return readiness_service.history(db, student, role_id)


@router.get("/readiness/gaps", response_model=list[GapResponse])
async def my_gaps(
    role_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> list[GapResponse]:
    """Gaps from the caller's latest stored readiness for a role."""
    student = student_service.get_or_create_me(db, user)
    return readiness_service.latest_gaps(db, student, role_id)


@router.get("/readiness/{student_id}", response_model=ReadinessResultResponse)
async def student_readiness(
    student_id: int,
    role_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReadinessResultResponse:
    """Latest stored readiness of a student; access rules match GET /students/{id}."""
    return readiness_service.staff_read(db, user, student_id, role_id)


@router.get("/career-roles", response_model=list[StudentCareerRoleResponse])
async def list_career_roles(
    user: User = StudentUser, db: Session = Depends(get_db)
) -> list[StudentCareerRoleResponse]:
    """Active career roles visible to the caller, flagged with ``is_goal``."""
    student = student_service.get_or_create_me(db, user)
    return career_goal_service.list_roles_for_student(db, student)


@router.get("/career-roles/{role_id}", response_model=StudentCareerRoleDetailResponse)
async def get_career_role(
    role_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> StudentCareerRoleDetailResponse:
    """A visible career role with its skills, goal flag and own stored readiness."""
    student = student_service.get_or_create_me(db, user)
    role = career_role_service.get_visible_role(db, student, role_id)
    return career_goal_service.role_detail_for_student(db, student, role)
