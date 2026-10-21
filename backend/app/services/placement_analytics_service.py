"""Extended placement analytics: role readiness, company eligibility counts, progress trends.

Aggregates only (no student identifiers). Eligibility counts come from the pure eligibility
engine over BULK-loaded students and academic records and are never combined with readiness.
Assumptions: role readiness counts a student only when they hold the role as a career goal;
a month's progress point averages each student's latest GENERAL score computed in that month.
"""
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.models import (
    AcademicRecord,
    CareerRole,
    Company,
    EligibilityRule,
    JobDescription,
    JobStatus,
    ReadinessScore,
    Student,
    StudentCareerGoal,
    User,
)
from app.schemas.placement_analytics import (
    CompanyEligibility,
    PlacementAnalyticsResponse,
    ProgressPoint,
    RoleReadiness,
)
from app.schemas.placement_dashboard import PlacementScope
from app.services import audit_service, department_service
from app.services import eligibility_engine as engine
from app.services.hod_dashboard_service import month_key, r2, ranked_scores, student_conds

DASHBOARD_PLACEMENT_ANALYTICS_READ = "DASHBOARD_PLACEMENT_ANALYTICS_READ"
ROLES_LIMIT = 15
JOBS_LIMIT = 20
TREND_MONTHS = 12


def _role_readiness(
    db: Session, college_id: int, dept_ids: list[int] | None
) -> list[RoleReadiness]:
    sf = student_conds(college_id, dept_ids)
    with_goal = func.count(func.distinct(StudentCareerGoal.student_id))
    goals = db.execute(
        select(StudentCareerGoal.career_role_id, CareerRole.name, with_goal)
        .join(Student, Student.id == StudentCareerGoal.student_id)
        .join(
            CareerRole,
            (CareerRole.id == StudentCareerGoal.career_role_id)
            & (CareerRole.college_id == college_id),
        )
        .where(StudentCareerGoal.college_id == college_id, *sf)
        .group_by(StudentCareerGoal.career_role_id, CareerRole.name)
        .order_by(with_goal.desc(), CareerRole.name)
        .limit(ROLES_LIMIT)
    ).all()
    if not goals:
        return []
    role_ids = [int(g[0]) for g in goals]
    r = ranked_scores(college_id, dept_ids, False)
    scored = {
        int(rid): (int(n), avg_o, avg_c)
        for rid, n, avg_o, avg_c in db.execute(
            select(r.c.role_id, func.count(r.c.overall), func.avg(r.c.overall),
                   func.avg(r.c.coverage))
            .join(
                StudentCareerGoal,
                (StudentCareerGoal.student_id == r.c.student_id)
                & (StudentCareerGoal.career_role_id == r.c.role_id),
            )
            .where(
                r.c.rn == 1,
                r.c.overall.is_not(None),
                r.c.role_id.in_(role_ids),
                StudentCareerGoal.college_id == college_id,
            )
            .group_by(r.c.role_id)
        ).all()
    }
    out: list[RoleReadiness] = []
    for rid, name, n_goal in goals:
        n, avg_o, avg_c = scored.get(int(rid), (0, None, None))
        out.append(
            RoleReadiness(
                role_id=int(rid), role_name=str(name), students_with_goal=int(n_goal),
                students_scored=n,
                average_overall=r2(avg_o) if avg_o is not None else None,
                average_coverage=r2(avg_c) if avg_c is not None else None,
            )
        )
    return out


def _company_eligibility(
    db: Session, college_id: int, dept_ids: list[int] | None
) -> list[CompanyEligibility]:
    jobs = db.execute(
        select(JobDescription.id, JobDescription.title, Company.name)
        .join(Company, Company.id == JobDescription.company_id)
        .where(
            JobDescription.college_id == college_id,
            Company.college_id == college_id,
            JobDescription.status == JobStatus.OPEN,
        )
        .order_by(
            JobDescription.application_deadline.is_(None),
            JobDescription.application_deadline,
            JobDescription.id,
        )
        .limit(JOBS_LIMIT)
    ).all()
    if not jobs:
        return []
    job_ids = [int(j[0]) for j in jobs]
    rules = {
        int(rule.job_id): rule
        for rule in db.execute(
            select(EligibilityRule).where(
                EligibilityRule.college_id == college_id, EligibilityRule.job_id.in_(job_ids)
            )
        ).scalars()
    }
    sf = student_conds(college_id, dept_ids)
    student_rows = db.execute(
        select(Student.id, Student.department_id, Student.graduation_year).where(*sf)
    ).all()
    records: dict[int, list[engine.RecordFact]] = defaultdict(list)
    for sid, sem, cgpa, arrears, att in db.execute(
        select(
            AcademicRecord.student_id, AcademicRecord.semester, AcademicRecord.cgpa,
            AcademicRecord.active_arrears, AcademicRecord.attendance_pct,
        )
        .join(Student, Student.id == AcademicRecord.student_id)
        .where(AcademicRecord.college_id == college_id, *sf)
    ).all():
        records[int(sid)].append(
            engine.RecordFact(
                semester=int(sem), cgpa=Decimal(str(cgpa)), active_arrears=int(arrears),
                attendance_pct=Decimal(str(att)) if att is not None else None,
            )
        )
    facts = [
        engine.StudentFacts(
            department_id=dept, graduation_year=grad, records=records.get(int(sid), ())
        )
        for sid, dept, grad in student_rows
    ]
    total = len(facts)
    out: list[CompanyEligibility] = []
    for job_id, title, company in jobs:
        row = rules.get(int(job_id))
        counts = {
            engine.ELIGIBLE: 0, engine.NOT_ELIGIBLE: 0, engine.INCOMPLETE_DATA: 0,
            engine.NO_RULE: 0,
        }
        rule_input: engine.RuleInput | None = None
        if row is not None:
            rule_input = engine.RuleInput(
                cgpa_min=row.cgpa_min,
                cgpa_basis=row.cgpa_basis.value if row.cgpa_basis is not None else None,
                max_arrears=row.max_arrears,
                attendance_min=row.attendance_min,
                department_ids=row.department_ids,
                graduation_years=row.graduation_years,
            )
        evaluable = rule_input is not None and (
            rule_input.cgpa_min is not None
            or rule_input.max_arrears is not None
            or rule_input.attendance_min is not None
            or rule_input.department_ids is not None
            or rule_input.graduation_years is not None
        )
        if evaluable:
            for fact in facts:
                counts[engine.evaluate(rule_input, fact).status] += 1
        else:
            counts[engine.NO_RULE] = total
        out.append(
            CompanyEligibility(
                job_id=int(job_id), job_title=str(title), company_name=str(company),
                eligible=counts[engine.ELIGIBLE], not_eligible=counts[engine.NOT_ELIGIBLE],
                incomplete_data=counts[engine.INCOMPLETE_DATA],
                no_rule_students=counts[engine.NO_RULE],
            )
        )
    return out


def _progress_trends(
    db: Session, college_id: int, dept_ids: list[int] | None
) -> list[ProgressPoint]:
    yr = extract("year", ReadinessScore.computed_at)
    mo = extract("month", ReadinessScore.computed_at)
    rn = func.row_number().over(
        partition_by=(ReadinessScore.student_id, yr, mo),
        order_by=(ReadinessScore.computed_at.desc(), ReadinessScore.id.desc()),
    )
    sub = (
        select(
            ReadinessScore.overall.label("overall"),
            yr.label("y"),
            mo.label("m"),
            rn.label("rn"),
        )
        .join(Student, Student.id == ReadinessScore.student_id)
        .where(
            ReadinessScore.college_id == college_id,
            ReadinessScore.role_id.is_(None),
            *student_conds(college_id, dept_ids),
        )
        .subquery()
    )
    scored = func.count(sub.c.overall)
    rows = db.execute(
        select(sub.c.y, sub.c.m, scored, func.avg(sub.c.overall))
        .where(sub.c.rn == 1)
        .group_by(sub.c.y, sub.c.m)
        .having(scored > 0)
        .order_by(sub.c.y.desc(), sub.c.m.desc())
        .limit(TREND_MONTHS)
    ).all()
    return [
        ProgressPoint(month=month_key(y, m), students_scored=int(n), average_overall=r2(avg))
        for y, m, n, avg in reversed(rows)
    ]


def build(db: Session, user: User, department_id: int | None) -> PlacementAnalyticsResponse:
    """Analytics for the caller's college (optionally one department)."""
    college_id = user.college_id
    scope = PlacementScope(department_id=None, department_name=None)
    if department_id is not None:
        dept = department_service.get_in_college(db, college_id, department_id)
        scope = PlacementScope(department_id=dept.id, department_name=dept.name)
    dept_ids = [department_id] if department_id is not None else None

    result = PlacementAnalyticsResponse(
        generated_at=datetime.now(UTC),
        scope=scope,
        role_readiness=_role_readiness(db, college_id, dept_ids),
        company_eligibility=_company_eligibility(db, college_id, dept_ids),
        progress_trends=_progress_trends(db, college_id, dept_ids),
    )
    audit_service.record(
        db, DASHBOARD_PLACEMENT_ANALYTICS_READ, "dashboard", user_id=user.id,
        college_id=college_id, resource_id=department_id,
    )
    db.commit()
    return result
