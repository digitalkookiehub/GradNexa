"""Schemas for the in-app step-by-step guide."""
from pydantic import BaseModel, Field


class GuideStep(BaseModel):
    """One concrete action in a procedure."""

    do: str
    detail: str | None = None
    expect: str | None = None


class GuideProblem(BaseModel):
    """A common problem and its fix."""

    problem: str
    fix: str


class GuideTerm(BaseModel):
    """A glossary entry (reference pages)."""

    term: str
    meaning: str


class GuideTable(BaseModel):
    """A small sample or reference table."""

    title: str
    columns: list[str]
    rows: list[list[str]]
    caption: str | None = None


class GuideProcedure(BaseModel):
    """A step-by-step procedure (or a reference page when it has terms and no steps)."""

    id: str
    title: str
    audience: str
    path: str | None = None
    summary: str
    before: list[str] = Field(default_factory=list)
    steps: list[GuideStep] = Field(default_factory=list)
    result: list[str] = Field(default_factory=list)
    problems: list[GuideProblem] = Field(default_factory=list)
    terms: list[GuideTerm] = Field(default_factory=list)
    tables: list[GuideTable] = Field(default_factory=list)
    note: str | None = None
    next: str | None = None


class GuideGroup(BaseModel):
    """A sidebar section holding related procedures."""

    id: str
    title: str
    intro: str | None = None
    procedures: list[GuideProcedure]


class GuideRole(BaseModel):
    """Who does what."""

    role: str
    does: str
    lands: str


class OverviewItem(BaseModel):
    """A box in the big-picture diagram, linking to a procedure."""

    id: str
    title: str
    summary: str
    goto: str


class GuideDocument(BaseModel):
    """The guide content file."""

    title: str
    tagline: str
    principles: list[str]
    roles: list[GuideRole]
    overview: list[OverviewItem]
    groups: list[GuideGroup]


class GuideResponse(GuideDocument):
    """Guide returned to the client: structured procedures plus the written version."""

    markdown: str
