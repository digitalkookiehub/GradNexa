"""HOD dashboard schemas (aggregates only; no student identifiers)."""
from datetime import datetime

from pydantic import BaseModel

from app.schemas.placement_dashboard import LevelCount, PlacementRule, PlacementTotals, TopGap


class HodScope(BaseModel):
    department_ids: list[int]
    department_names: list[str]


class SkillHeatCell(BaseModel):
    skill_id: int
    skill_name: str
    category_name: str
    students_assessed: int
    average_score: float | None


class CareerRoleCount(BaseModel):
    role_id: int
    role_name: str
    students: int


class AssessmentTrend(BaseModel):
    month: str
    submitted_attempts: int
    average_percentage: float | None


class HodDashboardResponse(BaseModel):
    generated_at: datetime
    scope: HodScope
    rule: PlacementRule | None
    rule_versions_in_use: list[int]
    totals: PlacementTotals
    level_distribution: list[LevelCount]
    skill_heatmap: list[SkillHeatCell]
    career_role_distribution: list[CareerRoleCount]
    assessment_trends: list[AssessmentTrend]
    training_priorities: list[TopGap]
