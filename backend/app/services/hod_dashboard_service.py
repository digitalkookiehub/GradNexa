"""HOD dashboard: aggregates for the HOD's assigned departments (never student identifiers).

Access: a HOD only sees departments in their HodAssignment rows. No assignments -> 403
"No department assigned"; a requested department_id outside the assignments -> 403.
All figures are deterministic aggregates computed in a bounded number of SQL statements.
The shared scope/ranking helpers here are also used by placement_analytics_service.
"""
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, case, distinct, extract, func, select
from sqlalchemy.orm import Session

from app.exceptions import ForbiddenError
from app.models import (
    AssessmentAttempt,
    AssessmentResult,
    AttemptStatus,
    CareerRole,
    Department,
    GapPriority,
    GapStatus,
    HodAssignment,
    ReadinessScore,
    Skill,
    SkillCategory,
    SkillGap,
    Student,
    StudentCareerGoal,
    StudentSkill,
    User,
)
from app.schemas.hod_dashboard import (
    AssessmentTrend,
    CareerRoleCount,
    HodDashboardResponse,
    HodScope,
    SkillHeatCell,
)
from app.schemas.placement_dashboard import LevelCount, PlacementRule, PlacementTotals, TopGap
from app.services import audit_service, readiness_rule_service
from app.services.placement_dashboard_service import _level_order

DASHBOARD_HOD_READ = "DASHBOARD_HOD_READ"
HEATMAP_LIMIT = 30
ROLES_LIMIT = 10
PRIORITIES_LIMIT = 10
TREND_MONTHS = 12


def r2(value: Any) -> float:
    """Round a numeric aggregate to 2 decimals as a float."""
    return round(float(Decimal(str(value))), 2)


def month_key(year: Any, month: Any) -> str:
    """'YYYY-MM' from extract() results."""
    return f"{int(year):04d}-{int(month):02d}"


def student_conds(college_id: int, department_ids: list[int] | None) -> list[Any]:
    """Student filters: the college, and optionally a set of departments."""
    conds: list[Any] = [Student.college_id == college_id]
    if department_ids is not None:
        conds.append(Student.department_id.in_(department_ids))
    return conds


def ranked_scores(college_id: int, department_ids: list[int] | None, general: bool) -> Any:
    """Subquery of stored scores ranked newest-first per student (and role)."""
    rn = func.row_number().over(
        partition_by=(ReadinessScore.student_id, ReadinessScore.role_id),
        order_by=(ReadinessScore.computed_at.desc(), ReadinessScore.id.desc()),
    )
    role_cond = (
        ReadinessScore.role_id.is_(None) if general else ReadinessScore.role_id.is_not(None)
    )
    return (
        select(
            ReadinessScore.id.label("id"),
            ReadinessScore.student_id.label("student_id"),
            ReadinessScore.role_id.label("role_id"),
            ReadinessScore.overall.label("overall"),
            ReadinessScore.level.label("level"),
            ReadinessScore.coverage.label("coverage"),
            ReadinessScore.rule_version.label("rule_version"),
            rn.label("rn"),
        )
        .join(Student, Student.id == ReadinessScore.student_id)
        .where(
            ReadinessScore.college_id == college_id,
            role_cond,
            *student_conds(college_id, department_ids),
        )
        .subquery()
    )


def top_gap_rows(
    db: Session, college_id: int, department_ids: list[int] | None, limit: int
) -> list[TopGap]:
    """Most common GAP skills in each student's latest stored gap set per role."""
    r = ranked_scores(college_id, department_ids, False)
    affected = func.count(distinct(SkillGap.student_id))
    high = func.count(distinct(case((SkillGap.priority == GapPriority.HIGH, SkillGap.student_id))))
    rows = db.execute(
        select(SkillGap.skill_id, Skill.name, affected, high)
        .join(r, r.c.id == SkillGap.readiness_score_id)
        .join(Skill, and_(Skill.id == SkillGap.skill_id, Skill.college_id == college_id))
        .where(
            r.c.rn == 1, SkillGap.college_id == college_id, SkillGap.status == GapStatus.GAP
        )
        .group_by(SkillGap.skill_id, Skill.name)
        .order_by(affected.desc(), high.desc(), Skill.name)
        .limit(limit)
    ).all()
    return [
        TopGap(
            skill_id=int(sid), skill_name=str(name),
            students_affected=int(n_aff), high_priority_students=int(n_high),
        )
        for sid, name, n_aff, n_high in rows
    ]


def assigned_department_ids(db: Session, user: User) -> list[int]:
    """Department ids the HOD is assigned to (403 when there are none)."""
    ids = [
        int(i)
        for i in db.execute(
            select(HodAssignment.department_id)
            .join(Department, Department.id == HodAssignment.department_id)
            .where(
                HodAssignment.college_id == user.college_id,
                HodAssignment.hod_user_id == user.id,
                Department.college_id == user.college_id,
            )
            .order_by(HodAssignment.department_id)
        ).scalars()
    ]
    if not ids:
        raise ForbiddenError("No department assigned")
    return ids


def build(db: Session, user: User, department_id: int | None) -> HodDashboardResponse:
    """Aggregate the HOD's assigned departments (or one of them)."""
    college_id = user.college_id
    assigned = assigned_department_ids(db, user)
    if department_id is not None and department_id not in assigned:
        raise ForbiddenError("Department not assigned to you")
    dept_ids = [department_id] if department_id is not None else assigned

    dept_names = [
        str(n)
        for n in db.execute(
            select(Department.name)
            .where(Department.college_id == college_id, Department.id.in_(dept_ids))
            .order_by(Department.name)
        ).scalars()
    ]
    rule = readiness_rule_service.get_active_rule(db, college_id)
    sf = student_conds(college_id, dept_ids)

    complete_expr = case(
        (
            and_(
                Student.department_id.is_not(None),
                Student.roll_number.is_not(None),
                Student.roll_number != "",
                Student.graduation_year.is_not(None),
            ),
            1,
        ),
        else_=0,
    )
    total_students, profile_complete = db.execute(
        select(func.count(Student.id), func.sum(complete_expr)).where(*sf)
    ).one()
    total_students = int(total_students or 0)

    g = ranked_scores(college_id, dept_ids, True)
    level_rows = db.execute(
        select(g.c.level, g.c.rule_version, func.count(g.c.id))
        .where(g.c.rn == 1)
        .group_by(g.c.level, g.c.rule_version)
    ).all()

    submitted = db.execute(
        select(func.count(distinct(AssessmentAttempt.student_id)))
        .join(Student, Student.id == AssessmentAttempt.student_id)
        .where(
            AssessmentAttempt.college_id == college_id,
            AssessmentAttempt.status == AttemptStatus.SUBMITTED,
            *sf,
        )
    ).scalar_one()

    assessed = func.count(distinct(StudentSkill.student_id))
    heat_rows = db.execute(
        select(
            StudentSkill.skill_id, Skill.name, SkillCategory.name, assessed,
            func.avg(StudentSkill.score),
        )
        .join(Student, Student.id == StudentSkill.student_id)
        .join(Skill, and_(Skill.id == StudentSkill.skill_id, Skill.college_id == college_id))
        .join(SkillCategory, SkillCategory.id == Skill.category_id)
        .where(StudentSkill.college_id == college_id, *sf)
        .group_by(StudentSkill.skill_id, Skill.name, SkillCategory.name)
        .order_by(assessed.desc(), Skill.name)
        .limit(HEATMAP_LIMIT)
    ).all()

    goal_count = func.count(distinct(StudentCareerGoal.student_id))
    role_rows = db.execute(
        select(StudentCareerGoal.career_role_id, CareerRole.name, goal_count)
        .join(Student, Student.id == StudentCareerGoal.student_id)
        .join(
            CareerRole,
            and_(
                CareerRole.id == StudentCareerGoal.career_role_id,
                CareerRole.college_id == college_id,
            ),
        )
        .where(StudentCareerGoal.college_id == college_id, *sf)
        .group_by(StudentCareerGoal.career_role_id, CareerRole.name)
        .order_by(goal_count.desc(), CareerRole.name)
        .limit(ROLES_LIMIT)
    ).all()

    yr = extract("year", AssessmentAttempt.submitted_at)
    mo = extract("month", AssessmentAttempt.submitted_at)
    trend_rows = db.execute(
        select(yr, mo, func.count(AssessmentAttempt.id), func.avg(AssessmentResult.percentage))
        .join(Student, Student.id == AssessmentAttempt.student_id)
        .outerjoin(AssessmentResult, AssessmentResult.attempt_id == AssessmentAttempt.id)
        .where(
            AssessmentAttempt.college_id == college_id,
            AssessmentAttempt.status == AttemptStatus.SUBMITTED,
            AssessmentAttempt.submitted_at.is_not(None),
            *sf,
        )
        .group_by(yr, mo)
        .order_by(yr.desc(), mo.desc())
        .limit(TREND_MONTHS)
    ).all()

    priorities = top_gap_rows(db, college_id, dept_ids, PRIORITIES_LIMIT)

    # ---- assemble ----
    level_counts: dict[str | None, int] = {}
    versions: set[int] = set()
    with_score = 0
    for level, version, count in level_rows:
        level_counts[level] = level_counts.get(level, 0) + int(count)
        versions.add(int(version))
        with_score += int(count)
    no_score = total_students - with_score
    if no_score > 0:
        level_counts[None] = level_counts.get(None, 0) + no_score
    order = _level_order(list(rule.level_thresholds)) if rule is not None else {}
    named = sorted(
        (lv for lv in level_counts if lv is not None),
        key=lambda lv: (0, order[lv], "") if lv in order else (1, 0, lv),
    )
    levels = [LevelCount(level=lv, count=level_counts[lv]) for lv in named if level_counts[lv] > 0]
    if level_counts.get(None, 0) > 0:
        levels.append(LevelCount(level=None, count=level_counts[None]))

    audit_service.record(
        db, DASHBOARD_HOD_READ, "dashboard", user_id=user.id, college_id=college_id,
        resource_id=department_id,
    )
    db.commit()

    return HodDashboardResponse(
        generated_at=datetime.now(UTC),
        scope=HodScope(department_ids=sorted(dept_ids), department_names=dept_names),
        rule=PlacementRule(id=rule.id, version=rule.version) if rule is not None else None,
        rule_versions_in_use=sorted(versions),
        totals=PlacementTotals(
            students=total_students,
            profile_complete=int(profile_complete or 0),
            with_readiness_score=with_score,
            with_assessment_submitted=int(submitted or 0),
        ),
        level_distribution=levels,
        skill_heatmap=[
            SkillHeatCell(
                skill_id=int(sid), skill_name=str(sn), category_name=str(cn),
                students_assessed=int(n), average_score=r2(avg) if avg is not None else None,
            )
            for sid, sn, cn, n, avg in heat_rows
        ],
        career_role_distribution=[
            CareerRoleCount(role_id=int(rid), role_name=str(rn), students=int(n))
            for rid, rn, n in role_rows
        ],
        assessment_trends=[
            AssessmentTrend(
                month=month_key(y, m), submitted_attempts=int(n),
                average_percentage=r2(avg) if avg is not None else None,
            )
            for y, m, n, avg in reversed(trend_rows)
        ],
        training_priorities=priorities,
    )
