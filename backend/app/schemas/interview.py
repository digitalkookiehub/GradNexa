"""Schemas for mock interviews and the interview question bank."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models import InterviewStatus

MAX_ANSWER_CHARS = 10000


# ---- student ---------------------------------------------------------------------------------
class InterviewStart(BaseModel):
    """Start (or resume) an interview for a role."""

    role_id: int
    question_count: int = Field(default=5, ge=1, le=10)


class InterviewQuestionOut(BaseModel):
    """A question as shown to the student (never includes the rubric)."""

    answer_id: int
    question_id: int
    position: int
    competency: str
    prompt: str
    min_words: int
    answer_text: str | None


class InterviewResponse(BaseModel):
    """An interview with its questions."""

    id: int
    role_id: int
    role_name: str | None
    status: InterviewStatus
    started_at: datetime
    completed_at: datetime | None
    questions: list[InterviewQuestionOut]


class InterviewListItem(BaseModel):
    """History row."""

    id: int
    role_id: int
    role_name: str | None
    status: InterviewStatus
    started_at: datetime
    completed_at: datetime | None
    overall: float | None


class AnswerIn(BaseModel):
    """One answer to save."""

    answer_id: int
    answer_text: str = Field(max_length=MAX_ANSWER_CHARS)


class AnswersSave(BaseModel):
    """Answers to save."""

    answers: list[AnswerIn]


class AnswersSaved(BaseModel):
    """Number of answers saved."""

    saved: int


class CompetencyScoreOut(BaseModel):
    """Competency mean."""

    competency: str
    score: float
    max: int = 100
    questions: int


class PerQuestionOut(BaseModel):
    """Per-question scoring detail."""

    question_id: int
    position: int
    prompt: str
    competency: str
    score: float
    answered: bool
    too_short: bool
    covered_concepts: list[str]
    missed_concepts: list[str]


class InterviewResultResponse(BaseModel):
    """Stored interview result."""

    id: int
    interview_id: int
    role_name: str | None
    overall: float | None
    competency_scores: list[CompetencyScoreOut]
    per_question: list[PerQuestionOut]
    computed_at: datetime
    scoring_version: str
    disclaimer: str


# ---- admin question bank ---------------------------------------------------------------------
class RubricConcept(BaseModel):
    """A concept with trigger keywords and weight."""

    concept: str = Field(min_length=1, max_length=200)
    keywords: list[str]
    weight: float = Field(gt=0, le=1000)

    @field_validator("concept")
    @classmethod
    def _concept(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("concept must not be blank")
        return v

    @field_validator("keywords")
    @classmethod
    def _keywords(cls, v: list[str]) -> list[str]:
        cleaned = [k.strip() for k in v if k and k.strip()]
        if not cleaned:
            raise ValueError("at least one non-blank keyword is required")
        if any(len(k) > 200 for k in cleaned):
            raise ValueError("keyword too long")
        return cleaned


def _check_rubric(v: list[RubricConcept]) -> list[RubricConcept]:
    if not v:
        raise ValueError("rubric needs at least one concept")
    return v


def _nonblank(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    if not v:
        raise ValueError("must not be blank")
    return v


class InterviewQuestionCreate(BaseModel):
    """Create a question."""

    role_id: int | None = None
    skill_id: int | None = None
    competency: str = Field(min_length=1, max_length=100)
    prompt: str = Field(min_length=1, max_length=5000)
    rubric: list[RubricConcept]
    min_words: int = Field(default=20, ge=0, le=2000)

    @field_validator("rubric")
    @classmethod
    def _rubric(cls, v: list[RubricConcept]) -> list[RubricConcept]:
        return _check_rubric(v)

    @field_validator("competency", "prompt")
    @classmethod
    def _blank(cls, v: str) -> str:
        return str(_nonblank(v))


class InterviewQuestionUpdate(BaseModel):
    """Partial update (role_id/skill_id may be set to null explicitly)."""

    role_id: int | None = None
    skill_id: int | None = None
    competency: str | None = Field(default=None, min_length=1, max_length=100)
    prompt: str | None = Field(default=None, min_length=1, max_length=5000)
    rubric: list[RubricConcept] | None = None
    min_words: int | None = Field(default=None, ge=0, le=2000)
    is_active: bool | None = None

    @field_validator("rubric")
    @classmethod
    def _rubric(cls, v: list[RubricConcept] | None) -> list[RubricConcept] | None:
        return None if v is None else _check_rubric(v)

    @field_validator("competency", "prompt")
    @classmethod
    def _blank(cls, v: str | None) -> str | None:
        return _nonblank(v)


class InterviewQuestionAdmin(BaseModel):
    """Admin view of a question including its rubric."""

    id: int
    role_id: int | None
    role_name: str | None
    skill_id: int | None
    competency: str
    prompt: str
    rubric: list[dict[str, Any]]
    min_words: int
    is_active: bool
    created_by: int
