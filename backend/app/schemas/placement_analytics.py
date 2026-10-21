"""Extended placement analytics schemas (aggregates only)."""
from datetime import datetime

from pydantic import BaseModel

from app.schemas.placement_dashboard import PlacementScope


class RoleReadiness(BaseModel):
    role_id: int
    role_name: str
    students_with_goal: int
    students_scored: int
    average_overall: float | None
    average_coverage: float | None


class CompanyEligibility(BaseModel):
    job_id: int
    job_title: str
    company_name: str
    eligible: int
    not_eligible: int
    incomplete_data: int
    no_rule_students: int


class ProgressPoint(BaseModel):
    month: str
    students_scored: int
    average_overall: float | None


class PlacementAnalyticsResponse(BaseModel):
    generated_at: datetime
    scope: PlacementScope
    role_readiness: list[RoleReadiness]
    company_eligibility: list[CompanyEligibility]
    progress_trends: list[ProgressPoint]
