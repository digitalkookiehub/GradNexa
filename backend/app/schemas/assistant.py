"""API schemas of the deterministic AI assistant."""
from typing import Literal

from pydantic import BaseModel, Field

IntentName = Literal[
    "readiness_for_role",
    "skill_gaps",
    "eligibility_for_job",
    "plan_status",
    "profile_summary",
    "knowledge_question",
]


class AssistantQuery(BaseModel):
    """Student question; role_id and job_id are optional explicit context."""

    question: str = Field(min_length=1, max_length=1000)
    role_id: int | None = Field(default=None, ge=1)
    job_id: int | None = Field(default=None, ge=1)


class Fact(BaseModel):
    """A labelled value taken from a deterministic service."""

    label: str
    value: str | int | float | bool | None


class AnswerSection(BaseModel):
    """A templated section of the answer."""

    heading: str
    text: str
    facts: list[Fact] = Field(default_factory=list)


class Citation(BaseModel):
    """A stored, approved knowledge passage backing a statement."""

    document_id: int
    document_title: str
    source_type: str
    chunk_id: int
    chunk_index: int
    snippet: str


class AssistantResponse(BaseModel):
    """Assistant answer: facts, citations and the tools that produced them."""

    question: str
    answer_sections: list[AnswerSection]
    citations: list[Citation]
    tools_used: list[str]
    intent: IntentName
    insufficient_evidence: bool
    llm_used: Literal[False] = False
    notes: list[str]
