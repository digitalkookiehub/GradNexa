"""Placement officer dashboard: college-scoped aggregates with a bounded query count."""
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, case, distinct, func, select
from sqlalchemy.orm import Session

from app.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentStatus,
    AttemptStatus,
    Department,
    GapPriority,
    GapStatus,
    ReadinessScore,
    Skill,
    SkillGap,
    Student,
    User,
)
from app.schemas.placement_dashboard import (
    AssessmentParticipation,
    DepartmentAggregate,
    LevelCount,
    PlacementDashboardResponse,
    PlacementRule,
    PlacementScope,
    PlacementTotals,
    TopGap,
)
from app.services import audit_service, department_service, readiness_rule_service

DASHBOARD_PLACEMENT_READ = "DASHBOARD_PLACEMENT_READ"
TOP_GAPS_LIMIT = 10
UNASSIGNED = "Unassigned"


def _r2(value: float) -> float:
    return round(float(value), 2)


def _student_filter(college_id: int, department_id: int | None) -> list[Any]:
    conds: list[Any] = [Student.college_id == college_id]
    if department_id is not None:
        conds.append(Student.department_id == department_id)
    return conds


def _ranked_scores(college_id: int, department_id: int | None, general: bool) -> Any:
    """Subquery of scores ranked newest-first per student and role."""
    rn = func.row_number().over(
        partition_by=(ReadinessScore.student_id, ReadinessScore.role_id),
        order_by=(ReadinessScore.computed_at.desc(), ReadinessScore.id.desc()),
    )
    role_cond = (
        ReadinessScore.role_id.is_(None) if general else ReadinessScore.role_id.is_not(None)
    )
    stmt = (
        select(
            ReadinessScore.id.label("id"),
            ReadinessScore.student_id.label("student_id"),
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
            *_student_filter(college_id, department_id),
        )
    )
    return stmt.subquery()


def _level_order(rule_levels: list[Any]) -> dict[str, int]:
    ordered = sorted(
        (t for t in rule_levels if isinstance(t, dict) and "level" in t and "min_score" in t),
        key=lambda t: float(t["min_score"]),
        reverse=True,
    )
    return {str(t["level"]): i for i, t in enumerate(ordered)}


def build(db: Session, user: User, department_id: int | None) -> PlacementDashboardResponse:
    """Aggregate placement readiness for the caller's college (optionally one department)."""
    college_id = user.college_id
    scope = PlacementScope(department_id=None, department_name=None)
    if department_id is not None:
        dept = department_service.get_in_college(db, college_id, department_id)
        scope = PlacementScope(department_id=dept.id, department_name=dept.name)

    rule = readiness_rule_service.get_active_rule(db, college_id)
    sf = _student_filter(college_id, department_id)

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
    student_rows = db.execute(
        select(Student.department_id, func.count(Student.id), func.sum(complete_expr))
        .where(*sf)
        .group_by(Student.department_id)
    ).all()

    dept_names: dict[int, str] = {
        int(i): str(n)
        for i, n in db.execute(
            select(Department.id, Department.name).where(Department.college_id == college_id)
        ).all()
    }

    # Latest general score per student.
    g = _ranked_scores(college_id, department_id, True)
    score_rows = db.execute(
        select(Student.department_id, g.c.level, g.c.overall, g.c.coverage, g.c.rule_version)
        .join(Student, Student.id == g.c.student_id)
        .where(g.c.rn == 1)
    ).all()

    # Top gaps from the latest stored gap set per student+role.
    r = _ranked_scores(college_id, department_id, False)
    affected = func.count(distinct(SkillGap.student_id))
    high = func.count(distinct(case((SkillGap.priority == GapPriority.HIGH, SkillGap.student_id))))
    gap_rows = db.execute(
        select(SkillGap.skill_id, Skill.name, affected, high)
        .join(r, r.c.id == SkillGap.readiness_score_id)
        .join(Skill, and_(Skill.id == SkillGap.skill_id, Skill.college_id == college_id))
        .where(
            r.c.rn == 1,
            SkillGap.college_id == college_id,
            SkillGap.status == GapStatus.GAP,
        )
        .group_by(SkillGap.skill_id, Skill.name)
        .order_by(affected.desc(), high.desc(), Skill.name)
        .limit(TOP_GAPS_LIMIT)
    ).all()

    # Assessment participation. With a department filter, count assessments of that
    # department plus college-wide (department-less) ones.
    pub_conds: list[Any] = [
        Assessment.college_id == college_id,
        Assessment.status == AssessmentStatus.PUBLISHED,
    ]
    if department_id is not None:
        pub_conds.append(
            (Assessment.department_id == department_id) | Assessment.department_id.is_(None)
        )
    published = db.execute(select(func.count(Assessment.id)).where(*pub_conds)).scalar_one()
    submitted = AssessmentAttempt.status == AttemptStatus.SUBMITTED
    att = db.execute(
        select(
            func.count(distinct(AssessmentAttempt.student_id)),
            func.count(distinct(case((submitted, AssessmentAttempt.student_id)))),
            func.sum(case((submitted, 1), else_=0)),
        )
        .join(Student, Student.id == AssessmentAttempt.student_id)
        .where(AssessmentAttempt.college_id == college_id, *sf)
    ).one()

    # ---- assemble ----
    total_students = sum(int(row[1]) for row in student_rows)
    profile_complete = sum(int(row[2] or 0) for row in student_rows)

    level_counts: dict[str | None, int] = {}
    per_dept: dict[int | None, dict[str, Any]] = {
        key: {"students": int(count), "scored": 0, "o": [], "c": []}
        for key, count, _ in student_rows
    }
    versions: set[int] = set()
    for dept_key, level, overall, coverage, version in score_rows:
        level_counts[level] = level_counts.get(level, 0) + 1
        versions.add(int(version))
        if overall is not None:
            bucket = per_dept[dept_key]
            bucket["scored"] += 1
            bucket["o"].append(float(Decimal(overall)))
            bucket["c"].append(float(Decimal(coverage)))
    with_score = len(score_rows)
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

    departments: list[DepartmentAggregate] = []
    for dept_key, b in per_dept.items():
        known = dept_key is not None and dept_key in dept_names
        departments.append(
            DepartmentAggregate(
                department_id=dept_key if known else None,
                department_name=dept_names[dept_key] if known and dept_key is not None
                else UNASSIGNED,
                students=b["students"],
                scored=b["scored"],
                avg_overall=_r2(sum(b["o"]) / len(b["o"])) if b["o"] else None,
                avg_coverage=_r2(sum(b["c"]) / len(b["c"])) if b["c"] else None,
            )
        )
    departments.sort(key=lambda d: d.department_name)

    audit_service.record(
        db, DASHBOARD_PLACEMENT_READ, "dashboard", user_id=user.id, college_id=college_id,
        resource_id=department_id,
    )
    db.commit()

    return PlacementDashboardResponse(
        generated_at=datetime.now(UTC),
        scope=scope,
        rule=PlacementRule(id=rule.id, version=rule.version) if rule is not None else None,
        rule_versions_in_use=sorted(versions),
        totals=PlacementTotals(
            students=total_students,
            profile_complete=profile_complete,
            with_readiness_score=with_score,
            with_assessment_submitted=int(att[1] or 0),
        ),
        level_distribution=levels,
        departments=departments,
        top_gaps=[
            TopGap(
                skill_id=int(sid), skill_name=str(name),
                students_affected=int(n_aff), high_priority_students=int(n_high),
            )
            for sid, name, n_aff, n_high in gap_rows
        ],
        assessment_participation=AssessmentParticipation(
            published_assessments=int(published),
            students_with_attempts=int(att[0] or 0),
            submitted_attempts=int(att[2] or 0),
        ),
    )
