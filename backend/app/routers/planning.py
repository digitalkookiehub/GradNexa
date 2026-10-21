"""STUDENT endpoints: career goals, approved learning resources and 30-day learning plans."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.planning import (
    GenerateRequest,
    GoalIn,
    GoalResponse,
    ItemStatusUpdate,
    PlanItemResponse,
    PlanResponse,
    PlanSummary,
    ReassessResponse,
    ResourcePublic,
)
from app.services import (
    career_goal_service,
    learning_plan_service,
    learning_resource_service,
    student_service,
)

router = APIRouter(tags=["planning"])
StudentUser = Depends(require_role(UserRole.STUDENT))


@router.get("/students/me/career-goals", response_model=list[GoalResponse])
async def get_goals(user: User = StudentUser, db: Session = Depends(get_db)) -> list[GoalResponse]:
    """The caller's career goals ordered by priority."""
    student = student_service.get_or_create_me(db, user)
    return career_goal_service.list_goals(db, student)


@router.put("/students/me/career-goals", response_model=list[GoalResponse])
async def put_goals(
    payload: list[GoalIn], user: User = StudentUser, db: Session = Depends(get_db)
) -> list[GoalResponse]:
    """Bulk replace the caller's career goals."""
    student = student_service.get_or_create_me(db, user)
    return career_goal_service.replace_goals(db, user, student, payload)


@router.get("/learning-resources", response_model=list[ResourcePublic])
async def list_resources(
    skill_id: int | None = None, user: User = StudentUser, db: Session = Depends(get_db)
) -> list[ResourcePublic]:
    """Approved learning resources of the caller's college."""
    return learning_resource_service.list_approved(db, user.college_id, skill_id)


@router.post("/plans/generate", response_model=PlanResponse, status_code=201)
async def generate_plan(
    payload: GenerateRequest, user: User = StudentUser, db: Session = Depends(get_db)
) -> PlanResponse:
    """Generate a 30-day plan from the latest stored gaps of a role."""
    student = student_service.get_or_create_me(db, user)
    return learning_plan_service.generate(
        db, user, student, payload.role_id, payload.skills_per_week
    )


@router.get("/plans/me", response_model=PlanResponse)
async def my_plan(user: User = StudentUser, db: Session = Depends(get_db)) -> PlanResponse:
    """The caller's active plan."""
    student = student_service.get_or_create_me(db, user)
    return learning_plan_service.get_active(db, student)


@router.get("/plans/me/history", response_model=list[PlanSummary])
async def my_plan_history(
    user: User = StudentUser, db: Session = Depends(get_db)
) -> list[PlanSummary]:
    """All of the caller's plans, newest first."""
    student = student_service.get_or_create_me(db, user)
    return learning_plan_service.history(db, student)


@router.post("/plans/me/reassess", response_model=ReassessResponse)
async def reassess_plan(
    user: User = StudentUser, db: Session = Depends(get_db)
) -> ReassessResponse:
    """Recompute readiness for the active plan's role and compare with its baseline."""
    student = student_service.get_or_create_me(db, user)
    return learning_plan_service.reassess(db, user, student)


@router.patch("/plans/items/{item_id}", response_model=PlanItemResponse)
async def update_item(
    item_id: int,
    payload: ItemStatusUpdate,
    user: User = StudentUser,
    db: Session = Depends(get_db),
) -> PlanItemResponse:
    """Change the status of one of the caller's plan items."""
    student = student_service.get_or_create_me(db, user)
    return learning_plan_service.update_item_status(db, user, student, item_id, payload.status)
