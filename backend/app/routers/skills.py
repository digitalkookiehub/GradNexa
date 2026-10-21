"""Skill catalogue (any authenticated user) and the student's own skill scores."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_role
from app.models import SkillCategory, User, UserRole
from app.schemas.assessment import SkillCategoryResponse, SkillResponse, StudentSkillResponse
from app.services import skill_service, student_service

router = APIRouter(tags=["skills"])


@router.get("/skills", response_model=list[SkillResponse])
async def list_skills(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[SkillResponse]:
    """Skills of the caller's college."""
    return skill_service.list_skills(db, user.college_id)


@router.get("/skill-categories", response_model=list[SkillCategoryResponse])
async def list_categories(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[SkillCategory]:
    """Skill categories of the caller's college."""
    return skill_service.list_categories(db, user.college_id)


@router.get("/students/me/skills", response_model=list[StudentSkillResponse])
async def my_skills(
    user: User = Depends(require_role(UserRole.STUDENT)), db: Session = Depends(get_db)
) -> list[StudentSkillResponse]:
    """The caller's current skill scores."""
    student = student_service.get_or_create_me(db, user)
    return skill_service.list_student_skills(db, user.college_id, student.id)
