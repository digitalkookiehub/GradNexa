"""ADMIN/FACULTY interview question bank endpoints."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.interview import (
    InterviewQuestionAdmin,
    InterviewQuestionCreate,
    InterviewQuestionUpdate,
)
from app.services import interview_question_service as svc

router = APIRouter(prefix="/admin/interview-questions", tags=["admin-interview-questions"])
Staff = Depends(require_role(UserRole.ADMIN, UserRole.FACULTY))


@router.get("", response_model=list[InterviewQuestionAdmin])
async def list_questions(
    role_id: int | None = None,
    active: bool | None = None,
    user: User = Staff,
    db: Session = Depends(get_db),
) -> list[InterviewQuestionAdmin]:
    """List interview questions of the caller's college."""
    return svc.list_questions(db, user.college_id, role_id, active)


@router.post("", response_model=InterviewQuestionAdmin, status_code=201)
async def create_question(
    payload: InterviewQuestionCreate, user: User = Staff, db: Session = Depends(get_db)
) -> InterviewQuestionAdmin:
    """Create an interview question with its rubric."""
    return svc.create(db, user.college_id, user.id, payload)


@router.put("/{question_id}", response_model=InterviewQuestionAdmin)
async def update_question(
    question_id: int,
    payload: InterviewQuestionUpdate,
    user: User = Staff,
    db: Session = Depends(get_db),
) -> InterviewQuestionAdmin:
    """Update an interview question."""
    return svc.update(db, user.college_id, user.id, question_id, payload)


@router.delete("/{question_id}", status_code=204)
async def delete_question(
    question_id: int, user: User = Staff, db: Session = Depends(get_db)
) -> Response:
    """Soft-delete (deactivate) an interview question."""
    svc.soft_delete(db, user.college_id, user.id, question_id)
    return Response(status_code=204)
