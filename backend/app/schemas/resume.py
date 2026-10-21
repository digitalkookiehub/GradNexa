"""Resume upload and analysis schemas."""
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class ResumeResponse(BaseModel):
    """Resume metadata (never includes the file or its storage key)."""

    id: int
    original_filename: str
    content_type: str
    size_bytes: int
    page_count: int | None
    uploaded_at: datetime
    has_text: bool
    text_length: int


class ResumeTextResponse(BaseModel):
    """Extracted text that all spans index into."""

    text: str


class AnalyzeRequest(BaseModel):
    """Analysis options."""

    role_id: int | None = None
    jd_text: str | None = Field(default=None, max_length=20000)
    job_id: int | None = None

    @model_validator(mode="after")
    def _job_xor_jd(self) -> "AnalyzeRequest":
        if self.job_id is not None and (self.jd_text or "").strip():
            raise ValueError("job_id and jd_text are mutually exclusive")
        return self


class Span(BaseModel):
    """Character range into the extracted text."""

    start: int
    end: int
    text: str


class Block(BaseModel):
    """Raw text block with its span."""

    text: str
    span: Span


class SkillHit(BaseModel):
    """A configured skill found in the text."""

    skill_id: int
    skill_name: str
    spans: list[Span]


class Extracted(BaseModel):
    """Deterministic extraction result."""

    sections_found: list[str]
    skills: list[SkillHit]
    education: list[Block]
    projects: list[Block]
    experience: list[Block]
    certifications: list[Block]


class RoleSkillRef(BaseModel):
    """Role skill requirement reference."""

    skill_id: int
    skill_name: str
    required_level: float
    weight: float


class RoleMatch(BaseModel):
    """Resume vs role skills."""

    match_percent: float | None
    found: list[RoleSkillRef]
    missing: list[RoleSkillRef]


class JdSkill(BaseModel):
    """Skill appearing in the job description."""

    skill_id: int
    skill_name: str
    in_resume: bool


class JdMatch(BaseModel):
    """Resume vs job description skills."""

    match_percent: float | None
    skills_in_jd: list[JdSkill]


class AnalysisResponse(BaseModel):
    """A stored analysis."""

    id: int
    resume_id: int
    role_id: int | None
    role_name: str | None
    extractor_version: str
    created_at: datetime
    extracted: Extracted
    role_match: RoleMatch | None
    jd_match: JdMatch | None
    notes: list[str]
    job_id: int | None = None
    job_title: str | None = None


class AnalysisSummary(BaseModel):
    """Analysis history row."""

    id: int
    created_at: datetime
    role_name: str | None
    has_jd: bool
    role_match_percent: float | None
