"""Student-facing job endpoints: list/detail, eligibility and skill-fit. STUDENT only."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.job_student import (
    EligibilityResponse,
    JobDetail,
    JobListItem,
    SkillFitResponse,
)
from app.services import job_student_service, student_service

router = APIRouter(prefix="/jobs", tags=["jobs"])
StudentUser = Depends(require_role(UserRole.STUDENT))


@router.get("", response_model=list[JobListItem])
async def list_jobs(
    user: User = StudentUser, db: Session = Depends(get_db)
) -> list[JobListItem]:
    """Open jobs of the caller's college with their eligibility status."""
    student = student_service.get_or_create_me(db, user)
    return job_student_service.list_jobs(db, student)


@router.get("/{job_id}", response_model=JobDetail)
async def get_job(
    job_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> JobDetail:
    """An open job with its skills and configured eligibility criteria."""
    student = student_service.get_or_create_me(db, user)
    return job_student_service.get_detail(db, student, job_id)


@router.get("/{job_id}/eligibility", response_model=EligibilityResponse)
async def get_eligibility(
    job_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> EligibilityResponse:
    """Whether the caller meets the configured eligibility criteria of the job."""
    student = student_service.get_or_create_me(db, user)
    return job_student_service.get_eligibility(db, user, student, job_id)


@router.get("/{job_id}/skill-fit", response_model=SkillFitResponse)
async def get_skill_fit(
    job_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> SkillFitResponse:
    """Skill gaps against the job's required skills."""
    student = student_service.get_or_create_me(db, user)
    return job_student_service.get_skill_fit(db, user, student, job_id)
