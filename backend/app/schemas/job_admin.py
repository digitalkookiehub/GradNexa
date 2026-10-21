"""Schemas for admin management of companies, jobs, job skills and eligibility rules."""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import CgpaBasis, JobStatus


def _clean_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    return value


def _check_website(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    lowered = value.lower()
    if not (lowered.startswith("http://") or lowered.startswith("https://")) or len(value) < 9:
        raise ValueError("website must start with http:// or https://")
    return value


class CompanyCreate(BaseModel):
    name: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    website: str | None = Field(default=None, max_length=500)

    _name = field_validator("name")(_clean_name)
    _web = field_validator("website")(_check_website)


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    website: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        return None if value is None else _clean_name(value)

    _web = field_validator("website")(_check_website)


class CompanyOut(BaseModel):
    id: int
    name: str
    description: str | None
    website: str | None
    is_active: bool
    job_count: int


class JobCreate(BaseModel):
    company_id: int
    title: str = Field(max_length=200)
    body: str = Field(max_length=20000)
    role_id: int | None = None
    application_deadline: date | None = None

    _title = field_validator("title")(_clean_name)
    _body = field_validator("body")(_clean_name)


class JobUpdate(BaseModel):
    """Fields present in the payload are applied; explicit null clears role_id / deadline."""

    title: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, max_length=20000)
    role_id: int | None = None
    application_deadline: date | None = None

    @field_validator("title", "body")
    @classmethod
    def _text(cls, value: str | None) -> str | None:
        return None if value is None else _clean_name(value)

    @model_validator(mode="after")
    def _not_null_text(self) -> "JobUpdate":
        for name in ("title", "body"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class JobSummary(BaseModel):
    id: int
    company_id: int
    company_name: str
    title: str
    role_id: int | None
    role_name: str | None
    status: JobStatus
    application_deadline: date | None
    has_eligibility_rule: bool


class JobSkillIn(BaseModel):
    skill_id: int
    required_level: float = Field(ge=0, le=100)
    weight: float = Field(gt=0, le=999)


class JobSkillOut(BaseModel):
    skill_id: int
    skill_name: str
    required_level: float
    weight: float


class DepartmentRef(BaseModel):
    id: int
    name: str


class EligibilityIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cgpa_min: float | None = Field(default=None, ge=0, le=10)
    cgpa_basis: CgpaBasis | None = None
    max_arrears: int | None = Field(default=None, ge=0)
    attendance_min: float | None = Field(default=None, ge=0, le=100)
    department_ids: list[int] | None = None
    graduation_years: list[int] | None = None
    custom_notes: list[str] | None = None

    @model_validator(mode="after")
    def _validate(self) -> "EligibilityIn":
        if (self.cgpa_min is None) != (self.cgpa_basis is None):
            raise ValueError("cgpa_min and cgpa_basis must be provided together")
        if self.department_ids is not None:
            if not self.department_ids:
                raise ValueError("department_ids must not be empty; use null for all")
            if len(set(self.department_ids)) != len(self.department_ids):
                raise ValueError("department_ids must be unique")
        if self.graduation_years is not None:
            if not self.graduation_years:
                raise ValueError("graduation_years must not be empty; use null for all")
            if any(y < 1990 or y > 2100 for y in self.graduation_years):
                raise ValueError("graduation_years must be between 1990 and 2100")
        if self.custom_notes is not None:
            if len(self.custom_notes) > 20:
                raise ValueError("at most 20 custom_notes")
            cleaned = [n.strip() for n in self.custom_notes]
            if any(not n or len(n) > 500 for n in cleaned):
                raise ValueError("each custom note must be 1-500 characters")
            self.custom_notes = cleaned
        return self


class EligibilityRuleOut(BaseModel):
    cgpa_min: float | None
    cgpa_basis: CgpaBasis | None
    max_arrears: int | None
    attendance_min: float | None
    department_ids: list[DepartmentRef] | None
    graduation_years: list[int] | None
    custom_notes: list[str]


class JobOut(JobSummary):
    body: str
    created_by: int | None
    skills: list[JobSkillOut]
    eligibility: EligibilityRuleOut | None


