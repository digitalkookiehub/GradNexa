"""Student profile endpoints. /me routes are STUDENT only."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_role
from app.models import AcademicRecord, Certification, Project, User, UserRole
from app.schemas.student import (
    AcademicRecordCreate,
    AcademicRecordResponse,
    AcademicRecordUpdate,
    CertificationCreate,
    CertificationResponse,
    ProjectCreate,
    ProjectResponse,
    StudentDetailResponse,
    StudentResponse,
    StudentUpdate,
)
from app.services import student_service

router = APIRouter(prefix="/students", tags=["students"])
StudentUser = Depends(require_role(UserRole.STUDENT))


@router.get("/me", response_model=StudentResponse)
async def get_me(user: User = StudentUser, db: Session = Depends(get_db)) -> StudentResponse:
    """Return (lazily creating) the caller's student profile."""
    return student_service.to_response(db, student_service.get_or_create_me(db, user))


@router.put("/me", response_model=StudentResponse)
async def update_me(
    payload: StudentUpdate, user: User = StudentUser, db: Session = Depends(get_db)
) -> StudentResponse:
    """Update the caller's student profile."""
    return student_service.to_response(db, student_service.update_me(db, user, payload))


@router.get("/me/academic-records", response_model=list[AcademicRecordResponse])
async def list_records(
    user: User = StudentUser, db: Session = Depends(get_db)
) -> list[AcademicRecord]:
    """List own academic records."""
    return student_service.list_records(db, student_service.get_or_create_me(db, user))


@router.post("/me/academic-records", response_model=AcademicRecordResponse, status_code=201)
async def create_record(
    payload: AcademicRecordCreate, user: User = StudentUser, db: Session = Depends(get_db)
) -> AcademicRecord:
    """Create an academic record."""
    student = student_service.get_or_create_me(db, user)
    return student_service.create_record(db, user, student, payload)


@router.put("/me/academic-records/{record_id}", response_model=AcademicRecordResponse)
async def update_record(
    record_id: int,
    payload: AcademicRecordUpdate,
    user: User = StudentUser,
    db: Session = Depends(get_db),
) -> AcademicRecord:
    """Update an academic record."""
    student = student_service.get_or_create_me(db, user)
    return student_service.update_record(db, user, student, record_id, payload)


@router.get("/me/projects", response_model=list[ProjectResponse])
async def list_projects(user: User = StudentUser, db: Session = Depends(get_db)) -> list[Project]:
    """List own projects."""
    return student_service.list_projects(db, student_service.get_or_create_me(db, user))


@router.post("/me/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    payload: ProjectCreate, user: User = StudentUser, db: Session = Depends(get_db)
) -> Project:
    """Create a project."""
    student = student_service.get_or_create_me(db, user)
    return student_service.create_project(db, user, student, payload)


@router.delete("/me/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> Response:
    """Delete a project."""
    student = student_service.get_or_create_me(db, user)
    student_service.delete_project(db, user, student, project_id)
    return Response(status_code=204)


@router.get("/me/certifications", response_model=list[CertificationResponse])
async def list_certifications(
    user: User = StudentUser, db: Session = Depends(get_db)
) -> list[Certification]:
    """List own certifications."""
    return student_service.list_certifications(db, student_service.get_or_create_me(db, user))


@router.post("/me/certifications", response_model=CertificationResponse, status_code=201)
async def create_certification(
    payload: CertificationCreate, user: User = StudentUser, db: Session = Depends(get_db)
) -> Certification:
    """Create a certification."""
    student = student_service.get_or_create_me(db, user)
    return student_service.create_certification(db, user, student, payload)


@router.delete("/me/certifications/{cert_id}", status_code=204)
async def delete_certification(
    cert_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> Response:
    """Delete a certification."""
    student = student_service.get_or_create_me(db, user)
    student_service.delete_certification(db, user, student, cert_id)
    return Response(status_code=204)


@router.get("/{student_id}", response_model=StudentDetailResponse)
async def get_student(
    student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> StudentDetailResponse:
    """Full student record; access rules are enforced in the service (HOD denied for now)."""
    return student_service.get_detail(db, user, student_id)
