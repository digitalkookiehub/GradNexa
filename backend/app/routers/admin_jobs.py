"""ADMIN/TPO job description, skill and eligibility management."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import JobStatus, User, UserRole
from app.schemas.job_admin import (
    EligibilityIn,
    EligibilityRuleOut,
    JobCreate,
    JobOut,
    JobSkillIn,
    JobSkillOut,
    JobSummary,
    JobUpdate,
)
from app.services import job_service as svc

router = APIRouter(prefix="/admin/jobs", tags=["admin-jobs"])
Staff = Depends(require_role(UserRole.ADMIN, UserRole.TPO))


@router.get("", response_model=list[JobSummary])
async def list_jobs(
    company_id: int | None = None,
    status: JobStatus | None = None,
    user: User = Staff,
    db: Session = Depends(get_db),
) -> list[JobSummary]:
    """Jobs of the college."""
    return svc.list_jobs(db, user.college_id, company_id, status)


@router.post("", response_model=JobOut, status_code=201)
async def create_job(
    payload: JobCreate, user: User = Staff, db: Session = Depends(get_db)
) -> JobOut:
    """Create a DRAFT job."""
    return svc.to_out(db, svc.create_job(db, user, payload))


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: int, user: User = Staff, db: Session = Depends(get_db)) -> JobOut:
    """One job with skills and eligibility."""
    return svc.to_out(db, svc.get_job(db, user.college_id, job_id))


@router.put("/{job_id}", response_model=JobOut)
async def update_job(
    job_id: int, payload: JobUpdate, user: User = Staff, db: Session = Depends(get_db)
) -> JobOut:
    """Update a job that is not closed."""
    return svc.to_out(db, svc.update_job(db, user, job_id, payload))


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: int, user: User = Staff, db: Session = Depends(get_db)) -> Response:
    """Delete a DRAFT job."""
    svc.delete_job(db, user, job_id)
    return Response(status_code=204)


@router.post("/{job_id}/publish", response_model=JobOut)
async def publish_job(job_id: int, user: User = Staff, db: Session = Depends(get_db)) -> JobOut:
    """DRAFT -> OPEN."""
    return svc.to_out(db, svc.publish_job(db, user, job_id))


@router.post("/{job_id}/close", response_model=JobOut)
async def close_job(job_id: int, user: User = Staff, db: Session = Depends(get_db)) -> JobOut:
    """OPEN -> CLOSED."""
    return svc.to_out(db, svc.close_job(db, user, job_id))


@router.put("/{job_id}/skills", response_model=list[JobSkillOut])
async def replace_skills(
    job_id: int, payload: list[JobSkillIn], user: User = Staff, db: Session = Depends(get_db)
) -> list[JobSkillOut]:
    """Bulk replace the job's required skills."""
    return svc.replace_skills(db, user, job_id, payload)


@router.put("/{job_id}/eligibility", response_model=EligibilityRuleOut)
async def set_eligibility(
    job_id: int, payload: EligibilityIn, user: User = Staff, db: Session = Depends(get_db)
) -> EligibilityRuleOut:
    """Upsert the job's eligibility rule."""
    return svc.set_eligibility(db, user, job_id, payload)


@router.delete("/{job_id}/eligibility", status_code=204)
async def delete_eligibility(
    job_id: int, user: User = Staff, db: Session = Depends(get_db)
) -> Response:
    """Remove the job's eligibility rule."""
    svc.delete_eligibility(db, user, job_id)
    return Response(status_code=204)
