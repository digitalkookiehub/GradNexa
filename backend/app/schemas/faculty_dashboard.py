"""Faculty dashboard schemas (assigned students only)."""
from datetime import datetime

from pydantic import BaseModel


class FacultyTotals(BaseModel):
    assigned_students: int
    with_readiness_score: int
    needing_support: int


class FacultyStudentRow(BaseModel):
    student_id: int
    name: str
    email: str
    department_name: str | None
    roll_number: str | None
    overall: float | None
    level: str | None
    coverage: float | None
    high_priority_gap_count: int
    last_assessment_percentage: float | None
    last_assessment_at: datetime | None
    needs_support: bool
    support_reasons: list[str]


class FacultyTopGap(BaseModel):
    skill_id: int
    skill_name: str
    students_affected: int
    high_priority_students: int


class FacultyAssessmentPerformance(BaseModel):
    assessment_id: int
    title: str
    attempts_submitted: int
    average_percentage: float | None


class FacultyDashboardResponse(BaseModel):
    generated_at: datetime
    totals: FacultyTotals
    students: list[FacultyStudentRow]
    top_gaps: list[FacultyTopGap]
    assessment_performance: list[FacultyAssessmentPerformance]
