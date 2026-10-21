"""Input and output models of the MCP tools (strict: unknown arguments are rejected)."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.job_student import (
    CompanyOut,
    EligibilityResponse,
    EligibilityRuleOut,
    JobDetail,
    JobSkillOut,
)


class StrictIn(BaseModel):
    """Base for tool inputs: reject unknown keys."""

    model_config = ConfigDict(extra="forbid")


# ---- inputs -------------------------------------------------------------------------------
class StudentIn(StrictIn):
    """Student-level tool input. Students must omit it or pass their own id."""

    student_id: int | None = Field(default=None, ge=1)


class AssessmentResultsIn(StudentIn):
    """Assessment results input."""

    limit: int = Field(default=10, ge=1, le=50)


class ProgressIn(StudentIn):
    """Progress input; role_id selects the role readiness (default latest of any kind)."""

    role_id: int | None = Field(default=None, ge=1)


class DepartmentIn(StrictIn):
    """Department details input; students may omit it to get their own department."""

    department_id: int | None = Field(default=None, ge=1)


class JobEligibilityIn(StrictIn):
    """Eligibility rules input; student_id (optional) adds an evaluation for that student."""

    job_id: int = Field(ge=1)
    student_id: int | None = Field(default=None, ge=1)


class CompanyIn(StrictIn):
    """Company requirements input."""

    company_id: int = Field(ge=1)


class JobIn(StrictIn):
    """Job description input."""

    job_id: int = Field(ge=1)


# ---- outputs ------------------------------------------------------------------------------
class ProfileOut(BaseModel):
    """Student profile."""

    student_id: int
    full_name: str
    department_id: int | None
    department_name: str | None
    roll_number: str | None
    graduation_year: int | None
    profile_complete: bool


class AcademicRecordItem(BaseModel):
    """One semester record."""

    semester: int
    cgpa: float
    active_arrears: int
    attendance_pct: float | None


class AcademicRecordOut(BaseModel):
    """Academic records including attendance."""

    student_id: int
    records: list[AcademicRecordItem]
    latest_semester: int | None
    latest_cgpa: float | None
    latest_attendance_pct: float | None


class AssessmentResultItem(BaseModel):
    """A submitted assessment result."""

    attempt_id: int
    assessment_title: str
    percentage: float
    total_score: float
    max_score: float
    submitted_at: datetime | None


class AssessmentResultsOut(BaseModel):
    """Recent assessment results (newest first)."""

    student_id: int
    results: list[AssessmentResultItem]


class SkillScoreItem(BaseModel):
    """A skill score derived from assessments."""

    skill_id: int
    skill_name: str
    category_name: str
    score: float
    evidence_count: int


class SkillScoresOut(BaseModel):
    """All skill scores of a student."""

    student_id: int
    skills: list[SkillScoreItem]


class GapItem(BaseModel):
    """A stored skill gap."""

    skill_id: int
    skill_name: str
    current: float | None
    required: float
    gap: float | None
    status: str
    priority: str
    recommended_action: str


class ReadinessSummary(BaseModel):
    """Summary of a stored readiness result (never recomputed here)."""

    role_id: int | None
    role_name: str | None
    overall: float | None
    level: str | None
    coverage: float
    rule_version: int
    computed_at: datetime
    gaps: list[GapItem]


class PlanProgress(BaseModel):
    """Progress of the active learning plan."""

    plan_id: int
    role_id: int
    role_name: str
    status: str
    starts_on: date
    done: int
    total: int
    percent: float


class ProgressOut(BaseModel):
    """Plan progress plus the latest stored readiness summary."""

    student_id: int
    plan: PlanProgress | None
    latest_readiness: ReadinessSummary | None


class RoleRef(BaseModel):
    """A career role reference."""

    id: int
    name: str


class DepartmentOut(BaseModel):
    """Department details."""

    department_id: int
    name: str
    code: str
    is_active: bool
    career_roles: list[RoleRef]


class EligibilityRulesOut(BaseModel):
    """Configured criteria of a job, with an evaluation only when a student is resolvable."""

    job_id: int
    job_title: str
    has_rule: bool
    criteria: EligibilityRuleOut | None
    evaluation: EligibilityResponse | None


class CompanyJob(BaseModel):
    """An OPEN job of a company with its required skills."""

    job_id: int
    title: str
    role_id: int | None
    application_deadline: date | None
    skills: list[JobSkillOut]


class CompanyRequirementsOut(BaseModel):
    """Company and the required skills of its OPEN jobs."""

    company: CompanyOut
    open_jobs: list[CompanyJob]


JobDescriptionOut = JobDetail
