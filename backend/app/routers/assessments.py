"""STUDENT assessment endpoints: listing, attempts, answers, submission, results, history."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.assessment import (
    AnswersPayload,
    AssessmentSummary,
    AttemptResponse,
    HistoryItem,
    ResultResponse,
    SavedResponse,
    StudentAssessmentSummary,
)
from app.services import attempt_service, student_service

router = APIRouter(tags=["assessments"])
StudentUser = Depends(require_role(UserRole.STUDENT))


@router.get("/assessments", response_model=list[StudentAssessmentSummary])
async def list_assessments(
    user: User = StudentUser, db: Session = Depends(get_db)
) -> list[StudentAssessmentSummary]:
    """Published assessments visible to the caller."""
    return attempt_service.list_for_student(db, student_service.get_or_create_me(db, user))


@router.get("/assessments/history", response_model=list[HistoryItem])
async def history(user: User = StudentUser, db: Session = Depends(get_db)) -> list[HistoryItem]:
    """Own results, newest first."""
    return attempt_service.history(db, student_service.get_or_create_me(db, user))


@router.get("/assessments/{assessment_id}", response_model=AssessmentSummary)
async def get_assessment(
    assessment_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> AssessmentSummary:
    """One visible assessment (no questions)."""
    return attempt_service.get_for_student(
        db, student_service.get_or_create_me(db, user), assessment_id
    )


@router.post("/assessments/{assessment_id}/attempts", response_model=AttemptResponse)
async def start_attempt(
    assessment_id: int,
    response: Response,
    user: User = StudentUser,
    db: Session = Depends(get_db),
) -> AttemptResponse:
    """Start a new attempt (201) or resume the in-progress one (200)."""
    student = student_service.get_or_create_me(db, user)
    attempt, created = attempt_service.start_attempt(db, user.id, student, assessment_id)
    response.status_code = 201 if created else 200
    return attempt


@router.put("/attempts/{attempt_id}/answers", response_model=SavedResponse)
async def save_answers(
    attempt_id: int,
    payload: AnswersPayload,
    user: User = StudentUser,
    db: Session = Depends(get_db),
) -> SavedResponse:
    """Save answers for an in-progress attempt."""
    student = student_service.get_or_create_me(db, user)
    return SavedResponse(
        saved=attempt_service.save_answers(db, student, attempt_id, payload.answers)
    )


@router.post("/attempts/{attempt_id}/submit", response_model=ResultResponse)
async def submit_attempt(
    attempt_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> ResultResponse:
    """Submit and score an attempt (idempotent)."""
    student = student_service.get_or_create_me(db, user)
    return attempt_service.submit(db, user.id, student, attempt_id)


@router.get("/attempts/{attempt_id}/result", response_model=ResultResponse)
async def get_result(
    attempt_id: int, user: User = StudentUser, db: Session = Depends(get_db)
) -> ResultResponse:
    """Result of an own finished attempt."""
    return attempt_service.get_result(db, student_service.get_or_create_me(db, user), attempt_id)
