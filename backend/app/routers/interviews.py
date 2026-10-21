"""Student mock interview endpoints (text-based, deterministic keyword-rubric scoring)."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.interview import (
    AnswersSave,
    AnswersSaved,
    InterviewListItem,
    InterviewResponse,
    InterviewResultResponse,
    InterviewStart,
)
from app.services import interview_service, student_service

router = APIRouter(prefix="/interviews", tags=["interviews"])
StudentUser = Depends(require_role(UserRole.STUDENT))


@router.post("", response_model=InterviewResponse, status_code=201)
async def start_interview(
    payload: InterviewStart,
    response: Response,
    user: User = StudentUser,
    db: Session = Depends(get_db),
) -> InterviewResponse:
    """Start an interview (201) or return the in-progress one for the role (200)."""
    student = student_service.get_or_create_me(db, user)
    interview, created = interview_service.start(
        db, user.id, student, payload.role_id, payload.question_count
    )
    if not created:
        response.status_code = 200
    return interview


@router.get("", response_model=list[InterviewListItem])
async def list_interviews(
    user: User = StudentUser, db: Session = Depends(get_db)
) -> list[InterviewListItem]:
    """The caller's interviews, newest first."""
    student = student_service.get_or_create_me(db, user)
    return interview_service.list_interviews(db, student)


@router.get("/{interview_id}", response_model=InterviewResponse)
async def get_interview(
    interview_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> InterviewResponse:
    """One of the caller's interviews."""
    student = student_service.get_or_create_me(db, user)
    return interview_service.get(db, student, interview_id)


@router.put("/{interview_id}/answers", response_model=AnswersSaved)
async def save_answers(
    interview_id: int,
    payload: AnswersSave,
    user: User = StudentUser,
    db: Session = Depends(get_db),
) -> AnswersSaved:
    """Save answers of an in-progress interview."""
    student = student_service.get_or_create_me(db, user)
    saved = interview_service.save_answers(db, student, interview_id, payload.answers)
    return AnswersSaved(saved=saved)


@router.post("/{interview_id}/finish", response_model=InterviewResultResponse)
async def finish_interview(
    interview_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> InterviewResultResponse:
    """Score the saved answers and complete the interview (idempotent)."""
    student = student_service.get_or_create_me(db, user)
    return interview_service.finish(db, user.id, student, interview_id)


@router.get("/{interview_id}/result", response_model=InterviewResultResponse)
async def interview_result(
    interview_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> InterviewResultResponse:
    """Stored result of a finished interview."""
    student = student_service.get_or_create_me(db, user)
    return interview_service.get_result(db, student, interview_id)
