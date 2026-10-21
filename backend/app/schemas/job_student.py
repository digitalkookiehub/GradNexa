"""Student-facing job, eligibility and skill-fit schemas."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.readiness import GapResponse

EligibilityStatus = Literal["ELIGIBLE", "NOT_ELIGIBLE", "INCOMPLETE_DATA", "NO_RULE"]
CriterionResult = Literal["MET", "NOT_MET", "UNKNOWN"]

ELIGIBILITY_NOTE = (
    "Eligibility reflects the configured criteria only. "
    "Custom notes are not evaluated automatically."
)


class JobListItem(BaseModel):
    """One open job in the student's college."""

    id: int
    company_id: int
    company_name: str
    title: str
    role_id: int | None
    role_name: str | None
    status: str
    application_deadline: date | None
    deadline_passed: bool
    has_eligibility_rule: bool
    eligibility_status: EligibilityStatus


class CompanyOut(BaseModel):
    """Company summary."""

    id: int
    name: str
    description: str | None
    website: str | None


class JobSkillOut(BaseModel):
    """A skill a job requires."""

    skill_id: int
    skill_name: str
    required_level: float
    weight: float


class DepartmentRef(BaseModel):
    """Department id and name."""

    id: int
    name: str


class EligibilityRuleOut(BaseModel):
    """Configured eligibility criteria of a job."""

    cgpa_min: float | None
    cgpa_basis: str | None
    max_arrears: int | None
    attendance_min: float | None
    department_ids: list[DepartmentRef] | None
    graduation_years: list[int] | None
    custom_notes: list[str]


class JobDetail(BaseModel):
    """Job detail."""

    id: int
    company: CompanyOut
    title: str
    body: str
    role_id: int | None
    role_name: str | None
    status: str
    application_deadline: date | None
    deadline_passed: bool
    skills: list[JobSkillOut]
    eligibility_criteria: EligibilityRuleOut | None


class CriterionOut(BaseModel):
    """One evaluated eligibility criterion."""

    key: str
    label: str
    required: str
    actual: str | None
    result: CriterionResult


class EligibilityResponse(BaseModel):
    """Deterministic evaluation of the configured criteria for the caller."""

    job_id: int
    status: EligibilityStatus
    criteria: list[CriterionOut]
    custom_notes: list[str]
    note: str = ELIGIBILITY_NOTE
    evaluated_at: datetime


class SkillFitResponse(BaseModel):
    """Skill gaps against a job's required skills (never mentions eligibility)."""

    job_id: int
    rule_id: int
    rule_version: int
    overall: float | None
    coverage: float
    gaps: list[GapResponse]
