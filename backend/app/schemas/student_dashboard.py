"""Response schemas for the student dashboard."""
from datetime import date, datetime

from pydantic import BaseModel

from app.models import GapPriority, GapStatus
from app.schemas.planning import Progress


class DashboardProfile(BaseModel):
    """Profile completeness summary."""

    profile_complete: bool
    department_name: str | None
    roll_number: str | None


class DashboardReadiness(BaseModel):
    """A stored readiness score summary."""

    overall: float | None
    level: str | None
    coverage: float
    rule_version: int
    computed_at: datetime


class DashboardRoleReadiness(DashboardReadiness):
    """Stored readiness for one career role."""

    role_id: int
    role_name: str | None


class DashboardReadinessBlock(BaseModel):
    """General and per-role readiness."""

    general: DashboardReadiness | None
    roles: list[DashboardRoleReadiness]


class DashboardSkill(BaseModel):
    """A skill the student has evidence for."""

    skill_id: int
    skill_name: str
    category_name: str
    score: float
    evidence_count: int


class DashboardGap(BaseModel):
    """A top skill gap for the source role."""

    role_id: int
    role_name: str | None
    skill_id: int
    skill_name: str
    current: float | None
    required: float
    gap: float | None
    status: GapStatus
    priority: GapPriority
    recommended_action: str


class DashboardGoal(BaseModel):
    """A career goal."""

    career_role_id: int
    role_name: str
    priority: int


class DashboardPlan(BaseModel):
    """The active learning plan."""

    id: int
    role_id: int
    role_name: str | None
    status: str
    starts_on: date
    progress: Progress


class DashboardAssessment(BaseModel):
    """A recently submitted assessment attempt."""

    attempt_id: int
    assessment_title: str
    percentage: float
    submitted_at: datetime | None


class DashboardResume(BaseModel):
    """The most recent resume analysis."""

    resume_id: int
    filename: str
    analyzed_at: datetime
    role_name: str | None
    role_match_percent: float | None


class DashboardInterviewLatest(BaseModel):
    """The most recent completed mock interview."""

    role_name: str | None
    overall: float | None
    computed_at: datetime


class DashboardInterview(BaseModel):
    """Mock interview progress (keyword-rubric coverage only)."""

    completed_count: int
    latest: DashboardInterviewLatest | None


class StudentDashboardResponse(BaseModel):
    """Everything the student dashboard shows, from stored data only."""

    profile: DashboardProfile
    rule_active: bool
    readiness: DashboardReadinessBlock
    skills: list[DashboardSkill]
    top_gaps: list[DashboardGap]
    goals: list[DashboardGoal]
    plan: DashboardPlan | None
    recent_assessments: list[DashboardAssessment]
    resume: DashboardResume | None
    interview: DashboardInterview
    not_implemented: list[str]
