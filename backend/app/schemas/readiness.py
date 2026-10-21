"""Pydantic schemas for readiness rules, career roles and readiness results."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import GapPriority, GapStatus


# ---- readiness rules ----------------------------------------------------------------------
class LevelThresholdIn(BaseModel):
    """A readiness level starting at ``min_score``."""

    level: str = Field(min_length=1, max_length=50)
    min_score: float = Field(ge=0, le=100)


class GapThresholdsIn(BaseModel):
    """Gap priority thresholds (points of gap)."""

    high_min_gap: float = Field(gt=0, le=100)
    medium_min_gap: float = Field(gt=0, le=100)


class ReadinessRuleCreate(BaseModel):
    """Create a new (inactive) rule version. All values are institutional policy."""

    weights: dict[str, float]
    level_thresholds: list[LevelThresholdIn]
    gap_thresholds: GapThresholdsIn


class ReadinessRuleResponse(BaseModel):
    """A stored readiness rule version."""

    id: int
    version: int
    is_active: bool
    weights: dict[str, float]
    level_thresholds: list[LevelThresholdIn]
    gap_thresholds: GapThresholdsIn
    created_by: int
    created_at: datetime


# ---- career roles -------------------------------------------------------------------------
class CareerRoleCreate(BaseModel):
    """Create a career role."""

    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    department_id: int | None = None
    is_active: bool = True


class CareerRoleUpdate(BaseModel):
    """Partially update a career role."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    department_id: int | None = None
    is_active: bool | None = None


class RoleSkillIn(BaseModel):
    """A skill requirement of a role."""

    skill_id: int
    required_level: float = Field(ge=0, le=100)
    weight: float = Field(gt=0, le=999)


class CareerRoleResponse(BaseModel):
    """Career role summary."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int | None
    name: str
    description: str | None
    is_active: bool


class RoleSkillResponse(BaseModel):
    """A role skill requirement with the skill name."""

    skill_id: int
    skill_name: str
    required_level: float
    weight: float


class CareerRoleDetailResponse(CareerRoleResponse):
    """Career role with its skill requirements."""

    skills: list[RoleSkillResponse]


# ---- readiness results --------------------------------------------------------------------
class GapResponse(BaseModel):
    """Gap analysis of one role skill."""

    skill_id: int
    skill_name: str
    current: float | None
    required: float
    gap: float | None
    status: GapStatus
    priority: GapPriority
    recommended_action: str


class CategoryScoreResponse(BaseModel):
    """Category score; score is null when the category has no evidence."""

    category_id: int
    category_name: str
    weight: float
    score: float | None
    evidence_count: int


class EvidenceResponse(BaseModel):
    """A skill score that contributed to the readiness result."""

    skill_id: int
    skill_name: str
    category_name: str
    score: float
    evidence_count: int
    last_result_id: int | None


class ReadinessComputeRequest(BaseModel):
    """Compute request; omit role_id for the general readiness score."""

    role_id: int | None = None


class ReadinessResultResponse(BaseModel):
    """A stored readiness result with its rule version, evidence and gaps."""

    id: int
    student_id: int
    role_id: int | None
    role_name: str | None
    rule_id: int
    rule_version: int
    overall: float | None
    level: str | None
    coverage: float
    category_scores: list[CategoryScoreResponse]
    evidence: list[EvidenceResponse]
    gaps: list[GapResponse]
    computed_at: datetime
