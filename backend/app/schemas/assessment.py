"""Pydantic schemas for skills, assessments, attempts and results."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import AssessmentStatus, AssessmentType, QuestionDifficulty, SkillScope


class Option(BaseModel):
    """An answer option."""

    id: str
    text: str


# ---- skills ---------------------------------------------------------------------------------
class SkillCategoryCreate(BaseModel):
    """Create a skill category."""

    name: str = Field(min_length=1, max_length=150)
    scope: SkillScope = SkillScope.COMMON
    department_id: int | None = None


class SkillCategoryUpdate(BaseModel):
    """Update a skill category."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    scope: SkillScope | None = None
    department_id: int | None = None


class SkillCategoryResponse(BaseModel):
    """Skill category."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    scope: SkillScope
    department_id: int | None


class SkillCreate(BaseModel):
    """Create a skill."""

    category_id: int
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None


class SkillUpdate(BaseModel):
    """Update a skill."""

    category_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None


class SkillResponse(BaseModel):
    """Skill with its category name."""

    id: int
    name: str
    description: str | None
    category_id: int
    category_name: str


class StudentSkillResponse(BaseModel):
    """A student's current skill score."""

    skill_id: int
    skill_name: str
    category_name: str
    score: float
    evidence_count: int
    confidence: float | None
    updated_at: datetime


# ---- assessments ----------------------------------------------------------------------------
class AssessmentCreate(BaseModel):
    """Create a DRAFT assessment."""

    title: str = Field(min_length=1, max_length=255)
    type: AssessmentType
    department_id: int | None = None
    time_limit_min: int | None = Field(default=None, gt=0)
    max_attempts: int | None = Field(default=None, gt=0)
    negative_marking: Decimal = Field(default=Decimal("0"), ge=0, le=1)


class AssessmentUpdate(BaseModel):
    """Update a DRAFT assessment; only fields sent are changed."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    type: AssessmentType | None = None
    department_id: int | None = None
    time_limit_min: int | None = Field(default=None, gt=0)
    max_attempts: int | None = Field(default=None, gt=0)
    negative_marking: Decimal | None = Field(default=None, ge=0, le=1)


class AssessmentSummary(BaseModel):
    """Assessment metadata without questions."""

    id: int
    series_key: str
    version: int
    title: str
    type: AssessmentType
    department_id: int | None
    time_limit_min: int | None
    max_attempts: int | None
    negative_marking: float
    status: AssessmentStatus
    question_count: int
    total_marks: float


class StudentAssessmentSummary(AssessmentSummary):
    """Summary plus the caller's attempt state."""

    attempts_used: int
    in_progress_attempt_id: int | None


class QuestionCreate(BaseModel):
    """Create a question inside a DRAFT assessment."""

    skill_id: int
    difficulty: QuestionDifficulty = QuestionDifficulty.MEDIUM
    body: str = Field(min_length=1)
    options: list[Option]
    correct_option_ids: list[str]
    marks: Decimal = Field(default=Decimal("1"), gt=0, le=999)
    position: int | None = Field(default=None, ge=0)


class QuestionUpdate(BaseModel):
    """Update a question; only fields sent are changed."""

    skill_id: int | None = None
    difficulty: QuestionDifficulty | None = None
    body: str | None = Field(default=None, min_length=1)
    options: list[Option] | None = None
    correct_option_ids: list[str] | None = None
    marks: Decimal | None = Field(default=None, gt=0, le=999)
    position: int | None = Field(default=None, ge=0)


class AdminQuestion(BaseModel):
    """Question including the answer key (staff only)."""

    id: int
    assessment_id: int
    skill_id: int
    skill_name: str
    difficulty: QuestionDifficulty
    body: str
    options: list[Option]
    correct_option_ids: list[str]
    marks: float
    position: int


class AdminAssessmentDetail(AssessmentSummary):
    """Assessment with all questions and answer keys."""

    created_by: int
    questions: list[AdminQuestion]


# ---- attempts -------------------------------------------------------------------------------
class AttemptQuestion(BaseModel):
    """A question as shown to a student (no answer key)."""

    id: int
    body: str
    options: list[Option]
    marks: float
    position: int
    skill_id: int
    skill_name: str
    multi_select: bool


class AttemptResponse(BaseModel):
    """An attempt with its questions and saved answers."""

    id: int
    assessment_id: int
    attempt_no: int
    status: str
    started_at: datetime
    expires_at: datetime | None
    questions: list[AttemptQuestion]
    answers: dict[str, list[str]]


class AnswersPayload(BaseModel):
    """Answers to save: {question_id: [option_id]}."""

    answers: dict[str, list[str]]


class SavedResponse(BaseModel):
    """Number of answers saved."""

    saved: int


class SkillScoreResponse(BaseModel):
    """Per-skill result."""

    skill_id: int
    skill_name: str
    score: float
    max: float
    percentage: float


class ResultResponse(BaseModel):
    """Assessment result (no answer keys)."""

    id: int
    attempt_id: int
    assessment_id: int
    assessment_title: str
    assessment_version: int
    total_score: float
    max_score: float
    percentage: float
    per_skill_scores: list[SkillScoreResponse]
    computed_at: datetime


class HistoryItem(ResultResponse):
    """Result plus attempt metadata."""

    submitted_at: datetime | None
    attempt_no: int
