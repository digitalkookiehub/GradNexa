"""Resume endpoints. STUDENT only, own data only. There is deliberately no download endpoint."""
from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.resume import (
    AnalysisResponse,
    AnalysisSummary,
    AnalyzeRequest,
    ResumeResponse,
    ResumeTextResponse,
)
from app.services import resume_service, student_service
from app.services.resume_text import PayloadTooLargeError

router = APIRouter(prefix="/resumes", tags=["resumes"])
StudentUser = Depends(require_role(UserRole.STUDENT))
_MULTIPART_SLACK = 1024 * 1024


@router.post("", response_model=ResumeResponse, status_code=201)
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    user: User = StudentUser,
    db: Session = Depends(get_db),
) -> ResumeResponse:
    """Upload a PDF or DOCX resume (validated by content)."""
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > max_bytes + _MULTIPART_SLACK:
        raise PayloadTooLargeError(f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit")
    data = await file.read(max_bytes + 1)
    student = student_service.get_or_create_me(db, user)
    return resume_service.to_response(
        resume_service.upload(db, user, student, file.filename, data)
    )


@router.get("", response_model=list[ResumeResponse])
async def list_resumes(
    user: User = StudentUser, db: Session = Depends(get_db)
) -> list[ResumeResponse]:
    """Own resumes, newest first."""
    student = student_service.get_or_create_me(db, user)
    return [resume_service.to_response(r) for r in resume_service.list_resumes(db, student)]


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> ResumeResponse:
    """One own resume."""
    student = student_service.get_or_create_me(db, user)
    return resume_service.to_response(resume_service.get_resume(db, student, resume_id))


@router.delete("/{resume_id}", status_code=204)
async def delete_resume(
    resume_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> Response:
    """Delete a resume, its analyses and the stored file."""
    student = student_service.get_or_create_me(db, user)
    resume_service.delete_resume(db, user, student, resume_id)
    return Response(status_code=204)


@router.get("/{resume_id}/text", response_model=ResumeTextResponse)
async def get_text(
    resume_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> ResumeTextResponse:
    """Extracted text that analysis spans index into."""
    student = student_service.get_or_create_me(db, user)
    return ResumeTextResponse(text=resume_service.get_resume(db, student, resume_id).extracted_text)


@router.post("/{resume_id}/analyze", response_model=AnalysisResponse, status_code=201)
async def analyze(
    resume_id: int,
    payload: AnalyzeRequest | None = None,
    user: User = StudentUser,
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    """Run the deterministic analysis (optionally against a role and/or job description)."""
    student = student_service.get_or_create_me(db, user)
    row = resume_service.analyze(db, user, student, resume_id, payload or AnalyzeRequest())
    return resume_service.to_analysis_response(db, row)


@router.get("/{resume_id}/analysis", response_model=AnalysisResponse)
async def latest_analysis(
    resume_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> AnalysisResponse:
    """Latest analysis."""
    student = student_service.get_or_create_me(db, user)
    return resume_service.latest_analysis(db, student, resume_id)


@router.get("/{resume_id}/analyses", response_model=list[AnalysisSummary])
async def list_analyses(
    resume_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> list[AnalysisSummary]:
    """Analysis history."""
    student = student_service.get_or_create_me(db, user)
    return resume_service.list_analyses(db, student, resume_id)
