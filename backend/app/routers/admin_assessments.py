"""ADMIN/FACULTY authoring endpoints plus ADMIN-only skill configuration."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import AssessmentStatus, QuestionDifficulty, SkillCategory, User, UserRole
from app.schemas.assessment import (
    AdminAssessmentDetail,
    AdminQuestion,
    AssessmentCreate,
    AssessmentSummary,
    AssessmentUpdate,
    QuestionCreate,
    QuestionUpdate,
    SkillCategoryCreate,
    SkillCategoryResponse,
    SkillCategoryUpdate,
    SkillCreate,
    SkillResponse,
    SkillUpdate,
)
from app.services import assessment_service as svc
from app.services import skill_service

router = APIRouter(prefix="/admin", tags=["admin-assessments"])
Staff = Depends(require_role(UserRole.ADMIN, UserRole.FACULTY))
AdminOnly = Depends(require_role(UserRole.ADMIN))


@router.get("/assessments", response_model=list[AssessmentSummary])
async def list_assessments(
    status: AssessmentStatus | None = None,
    type: str | None = None,
    user: User = Staff,
    db: Session = Depends(get_db),
) -> list[AssessmentSummary]:
    """List assessments of the caller's college."""
    return svc.list_assessments(db, user.college_id, status, type)


@router.post("/assessments", response_model=AssessmentSummary, status_code=201)
async def create_assessment(
    payload: AssessmentCreate, user: User = Staff, db: Session = Depends(get_db)
) -> AssessmentSummary:
    """Create a DRAFT assessment."""
    return svc.to_summary(db, svc.create(db, user.college_id, user.id, payload))


@router.get("/assessments/{assessment_id}", response_model=AdminAssessmentDetail)
async def get_assessment(
    assessment_id: int, user: User = Staff, db: Session = Depends(get_db)
) -> AdminAssessmentDetail:
    """Assessment with questions and answer keys."""
    return svc.get_detail(db, user.college_id, assessment_id)


@router.put("/assessments/{assessment_id}", response_model=AssessmentSummary)
async def update_assessment(
    assessment_id: int,
    payload: AssessmentUpdate,
    user: User = Staff,
    db: Session = Depends(get_db),
) -> AssessmentSummary:
    """Update a DRAFT assessment."""
    return svc.to_summary(db, svc.update(db, user.college_id, user.id, assessment_id, payload))


@router.delete("/assessments/{assessment_id}", status_code=204)
async def delete_assessment(
    assessment_id: int, user: User = Staff, db: Session = Depends(get_db)
) -> Response:
    """Delete a DRAFT assessment without attempts."""
    svc.delete(db, user.college_id, user.id, assessment_id)
    return Response(status_code=204)


@router.post("/assessments/{assessment_id}/publish", response_model=AssessmentSummary)
async def publish_assessment(
    assessment_id: int, user: User = Staff, db: Session = Depends(get_db)
) -> AssessmentSummary:
    """Publish a DRAFT assessment."""
    return svc.to_summary(db, svc.publish(db, user.college_id, user.id, assessment_id))


@router.post("/assessments/{assessment_id}/archive", response_model=AssessmentSummary)
async def archive_assessment(
    assessment_id: int, user: User = Staff, db: Session = Depends(get_db)
) -> AssessmentSummary:
    """Archive a PUBLISHED assessment."""
    return svc.to_summary(db, svc.archive(db, user.college_id, user.id, assessment_id))


@router.post(
    "/assessments/{assessment_id}/new-version", response_model=AssessmentSummary, status_code=201
)
async def new_version(
    assessment_id: int, user: User = Staff, db: Session = Depends(get_db)
) -> AssessmentSummary:
    """Clone a PUBLISHED/ARCHIVED assessment into a new DRAFT version."""
    return svc.to_summary(db, svc.new_version(db, user.college_id, user.id, assessment_id))


@router.get("/question-bank", response_model=list[AdminQuestion])
async def question_bank(
    skill_id: int | None = None,
    difficulty: QuestionDifficulty | None = None,
    assessment_id: int | None = None,
    user: User = Staff,
    db: Session = Depends(get_db),
) -> list[AdminQuestion]:
    """Questions across the college."""
    return svc.question_bank(db, user.college_id, skill_id, difficulty, assessment_id)


@router.post(
    "/assessments/{assessment_id}/questions", response_model=AdminQuestion, status_code=201
)
async def add_question(
    assessment_id: int,
    payload: QuestionCreate,
    user: User = Staff,
    db: Session = Depends(get_db),
) -> AdminQuestion:
    """Add a question to a DRAFT assessment."""
    return svc.add_question(db, user.college_id, user.id, assessment_id, payload)


@router.put("/question-bank/{question_id}", response_model=AdminQuestion)
async def update_question(
    question_id: int, payload: QuestionUpdate, user: User = Staff, db: Session = Depends(get_db)
) -> AdminQuestion:
    """Update a question of a DRAFT assessment."""
    return svc.update_question(db, user.college_id, user.id, question_id, payload)


@router.delete("/question-bank/{question_id}", status_code=204)
async def delete_question(
    question_id: int, user: User = Staff, db: Session = Depends(get_db)
) -> Response:
    """Delete a question of a DRAFT assessment."""
    svc.delete_question(db, user.college_id, user.id, question_id)
    return Response(status_code=204)


# ---- skill configuration (ADMIN only) -------------------------------------------------------
@router.post("/skill-categories", response_model=SkillCategoryResponse, status_code=201)
async def create_category(
    payload: SkillCategoryCreate, user: User = AdminOnly, db: Session = Depends(get_db)
) -> SkillCategory:
    """Create a skill category."""
    return skill_service.create_category(db, user.college_id, user.id, payload)


@router.put("/skill-categories/{category_id}", response_model=SkillCategoryResponse)
async def update_category(
    category_id: int,
    payload: SkillCategoryUpdate,
    user: User = AdminOnly,
    db: Session = Depends(get_db),
) -> SkillCategory:
    """Update a skill category."""
    return skill_service.update_category(db, user.college_id, user.id, category_id, payload)


@router.post("/skills", response_model=SkillResponse, status_code=201)
async def create_skill(
    payload: SkillCreate, user: User = AdminOnly, db: Session = Depends(get_db)
) -> SkillResponse:
    """Create a skill."""
    return skill_service.create_skill(db, user.college_id, user.id, payload)


@router.put("/skills/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: int, payload: SkillUpdate, user: User = AdminOnly, db: Session = Depends(get_db)
) -> SkillResponse:
    """Update a skill."""
    return skill_service.update_skill(db, user.college_id, user.id, skill_id, payload)
