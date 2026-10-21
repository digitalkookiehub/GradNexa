"""Placement officer dashboard schemas (aggregates only; no student identifiers)."""
from datetime import datetime

from pydantic import BaseModel


class PlacementScope(BaseModel):
    department_id: int | None
    department_name: str | None


class PlacementRule(BaseModel):
    id: int
    version: int


class PlacementTotals(BaseModel):
    students: int
    profile_complete: int
    with_readiness_score: int
    with_assessment_submitted: int


class LevelCount(BaseModel):
    level: str | None
    count: int


class DepartmentAggregate(BaseModel):
    department_id: int | None
    department_name: str
    students: int
    scored: int
    avg_overall: float | None
    avg_coverage: float | None


class TopGap(BaseModel):
    skill_id: int
    skill_name: str
    students_affected: int
    high_priority_students: int


class AssessmentParticipation(BaseModel):
    published_assessments: int
    students_with_attempts: int
    submitted_attempts: int


class PlacementDashboardResponse(BaseModel):
    generated_at: datetime
    scope: PlacementScope
    rule: PlacementRule | None
    rule_versions_in_use: list[int]
    totals: PlacementTotals
    level_distribution: list[LevelCount]
    departments: list[DepartmentAggregate]
    top_gaps: list[TopGap]
    assessment_participation: AssessmentParticipation
