"""Pydantic schemas for career goals, learning resources and learning plans."""
from datetime import date, datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from app.models import PlanItemKind, PlanItemStatus, PlanStatus
from app.schemas.readiness import (
    CareerRoleDetailResponse,
    CareerRoleResponse,
    ReadinessResultResponse,
)


def _check_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("url must be an http or https URL")
    return value.strip()


# ---- career goals / roles -----------------------------------------------------------------
class GoalIn(BaseModel):
    """A career goal in a bulk replace payload."""

    career_role_id: int
    priority: int = Field(ge=1, le=1000)


class GoalResponse(BaseModel):
    """A student's career goal."""

    career_role_id: int
    role_name: str
    priority: int


class MyReadiness(BaseModel):
    """Summary of the student's latest stored role readiness."""

    overall: float | None
    level: str | None
    coverage: float
    rule_version: int
    computed_at: datetime


class StudentCareerRoleResponse(CareerRoleResponse):
    """Role list item for students, with the goal flag."""

    is_goal: bool = False


class StudentCareerRoleDetailResponse(CareerRoleDetailResponse):
    """Role detail for students: goal flag and own stored readiness."""

    is_goal: bool = False
    my_readiness: MyReadiness | None = None


# ---- learning resources -------------------------------------------------------------------
class ResourceCreate(BaseModel):
    """Create a (unapproved) learning resource."""

    skill_id: int
    title: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=2048)
    description: str | None = None

    @field_validator("url")
    @classmethod
    def _url(cls, value: str) -> str:
        return _check_url(value)


class ResourceUpdate(BaseModel):
    """Partial resource update; changing url or skill resets approval."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    description: str | None = None
    skill_id: int | None = None

    @field_validator("url")
    @classmethod
    def _url(cls, value: str | None) -> str | None:
        return None if value is None else _check_url(value)


class ResourcePublic(BaseModel):
    """An approved resource as shown to students."""

    id: int
    skill_id: int
    skill_name: str
    title: str
    url: str
    description: str | None


class ResourceAdmin(ResourcePublic):
    """A resource with its approval state (staff view)."""

    is_approved: bool
    approved_by: int | None
    approved_at: datetime | None
    created_by: int


# ---- plans --------------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    """Plan generation request."""

    role_id: int
    skills_per_week: int = Field(default=2, ge=1, le=5)


class ItemStatusUpdate(BaseModel):
    """Item status change."""

    status: PlanItemStatus


class ItemResource(BaseModel):
    """Resource attached to a plan item."""

    id: int
    title: str
    url: str


class PlanItemResponse(BaseModel):
    """A plan item."""

    id: int
    week: int
    position: int
    kind: PlanItemKind
    skill_id: int | None
    skill_name: str | None
    resource: ItemResource | None
    task: str
    status: PlanItemStatus
    completed_at: datetime | None


class PlanWeek(BaseModel):
    """One week of a plan."""

    week: int
    items: list[PlanItemResponse]


class PlanBaseline(BaseModel):
    """The readiness score the plan was generated from."""

    readiness_score_id: int
    overall: float | None
    level: str | None
    rule_version: int
    computed_at: datetime


class UnscheduledSkill(BaseModel):
    """A gap skill that did not fit in the plan."""

    skill_id: int
    skill_name: str
    gap: float | None


class Progress(BaseModel):
    """Completed items out of total."""

    done: int
    total: int
    percent: float


class PlanResponse(BaseModel):
    """A full learning plan."""

    id: int
    role_id: int
    role_name: str
    status: PlanStatus
    starts_on: date
    duration_days: int
    skills_per_week: int
    baseline: PlanBaseline | None
    weeks: list[PlanWeek]
    unscheduled_skills: list[UnscheduledSkill]
    progress: Progress


class PlanSummary(BaseModel):
    """History row."""

    id: int
    role_id: int
    role_name: str
    status: PlanStatus
    starts_on: date
    progress: Progress


class ReassessBaseline(BaseModel):
    """Baseline summary in a reassessment."""

    overall: float | None
    level: str | None
    rule_version: int


class SkillChange(BaseModel):
    """Per-skill evidence score change."""

    skill_id: int
    skill_name: str
    before: float | None
    after: float | None
    delta: float | None


class ReassessResponse(BaseModel):
    """Result of a plan reassessment."""

    plan_id: int
    baseline: ReassessBaseline | None
    current: ReadinessResultResponse
    overall_delta: float | None
    rule_version_changed: bool
    skill_changes: list[SkillChange]
