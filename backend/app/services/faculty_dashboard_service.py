"""Faculty dashboard: readiness overview of the caller's ASSIGNED students only.

Faculty may see names/emails/ids of assigned students (same access rule as
GET /students/{id}); unassigned students of the same college never appear.

needs_support rule (ASSUMPTION: unconfirmed institutional policy, to be confirmed by the
college). A student needs support when ANY of these hold, each adding a factual reason:
  1. no stored general readiness score            -> "No readiness score yet"
  2. latest general score has a null overall      -> "Not enough evidence yet"
  3. >=1 HIGH-priority GAP in the latest stored gap set of any role (distinct skills)
                                                  -> "N high-priority skill gaps"
No thresholds or predictions are involved. The query count is independent of student count.
"""
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, case, distinct, func, select
from sqlalchemy.orm import Session

from app.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentResult,
    AttemptStatus,
    Department,
    FacultyAssignment,
    GapPriority,
    GapStatus,
    ReadinessScore,
    Skill,
    SkillGap,
    Student,
    User,
)
from app.schemas.faculty_dashboard import (
    FacultyAssessmentPerformance,
    FacultyDashboardResponse,
    FacultyStudentRow,
    FacultyTopGap,
    FacultyTotals,
)
from app.services import audit_service
from app.services.hod_dashboard_service import r2

DASHBOARD_FACULTY_READ = "DASHBOARD_FACULTY_READ"
LIMIT = 10
REASON_NO_SCORE = "No readiness score yet"
REASON_NO_EVIDENCE = "Not enough evidence yet"


def _assigned_ids(college_id: int, faculty_id: int) -> Any:
    return (
        select(FacultyAssignment.student_id)
        .join(Student, Student.id == FacultyAssignment.student_id)
        .where(
            FacultyAssignment.college_id == college_id,
            FacultyAssignment.faculty_user_id == faculty_id,
            Student.college_id == college_id,
        )
    )


def _ranked_scores(college_id: int, faculty_id: int, general: bool) -> Any:
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
            ReadinessScore.overall.label("overall"),
            ReadinessScore.level.label("level"),
            ReadinessScore.coverage.label("coverage"),
            rn.label("rn"),
        )
        .where(
            ReadinessScore.college_id == college_id,
            role_cond,
            ReadinessScore.student_id.in_(_assigned_ids(college_id, faculty_id)),
        )
        .subquery()
    )


def build(db: Session, user: User) -> FacultyDashboardResponse:
    """Dashboard for the faculty user's assigned students."""
    college_id, fid = user.college_id, user.id

    students = db.execute(
        select(
            Student.id, User.full_name, User.email, Department.name, Student.roll_number
        )
        .join(User, User.id == Student.user_id)
        .outerjoin(
            Department,
            and_(Department.id == Student.department_id, Department.college_id == college_id),
        )
        .where(Student.id.in_(_assigned_ids(college_id, fid)), Student.college_id == college_id)
    ).all()

    g = _ranked_scores(college_id, fid, True)
    scores = {
        int(sid): (overall, level, coverage)
        for sid, overall, level, coverage in db.execute(
            select(g.c.student_id, g.c.overall, g.c.level, g.c.coverage).where(g.c.rn == 1)
        ).all()
    }

    r = _ranked_scores(college_id, fid, False)
    high_counts = {
        int(sid): int(n)
        for sid, n in db.execute(
            select(SkillGap.student_id, func.count(distinct(SkillGap.skill_id)))
            .join(r, r.c.id == SkillGap.readiness_score_id)
            .where(
                r.c.rn == 1,
                SkillGap.college_id == college_id,
                SkillGap.status == GapStatus.GAP,
                SkillGap.priority == GapPriority.HIGH,
            )
            .group_by(SkillGap.student_id)
        ).all()
    }

    rr = func.row_number().over(
        partition_by=AssessmentResult.student_id,
        order_by=(AssessmentResult.computed_at.desc(), AssessmentResult.id.desc()),
    )
    res_sub = (
        select(
            AssessmentResult.student_id.label("student_id"),
            AssessmentResult.percentage.label("percentage"),
            AssessmentResult.computed_at.label("computed_at"),
            rr.label("rn"),
        )
        .where(
            AssessmentResult.college_id == college_id,
            AssessmentResult.student_id.in_(_assigned_ids(college_id, fid)),
        )
        .subquery()
    )
    last_results = {
        int(sid): (pct, at)
        for sid, pct, at in db.execute(
            select(res_sub.c.student_id, res_sub.c.percentage, res_sub.c.computed_at).where(
                res_sub.c.rn == 1
            )
        ).all()
    }

    affected = func.count(distinct(SkillGap.student_id))
    high = func.count(distinct(case((SkillGap.priority == GapPriority.HIGH, SkillGap.student_id))))
    gap_rows = db.execute(
        select(SkillGap.skill_id, Skill.name, affected, high)
        .join(r, r.c.id == SkillGap.readiness_score_id)
        .join(Skill, and_(Skill.id == SkillGap.skill_id, Skill.college_id == college_id))
        .where(
            r.c.rn == 1, SkillGap.college_id == college_id, SkillGap.status == GapStatus.GAP
        )
        .group_by(SkillGap.skill_id, Skill.name)
        .order_by(affected.desc(), high.desc(), Skill.name)
        .limit(LIMIT)
    ).all()

    attempts = func.count(AssessmentAttempt.id)
    perf_rows = db.execute(
        select(Assessment.id, Assessment.title, attempts, func.avg(AssessmentResult.percentage))
        .join(Assessment, and_(
            Assessment.id == AssessmentAttempt.assessment_id,
            Assessment.college_id == college_id,
        ))
        .outerjoin(AssessmentResult, AssessmentResult.attempt_id == AssessmentAttempt.id)
        .where(
            AssessmentAttempt.college_id == college_id,
            AssessmentAttempt.status == AttemptStatus.SUBMITTED,
            AssessmentAttempt.student_id.in_(_assigned_ids(college_id, fid)),
        )
        .group_by(Assessment.id, Assessment.title)
        .order_by(attempts.desc(), Assessment.title, Assessment.id)
        .limit(LIMIT)
    ).all()

    rows: list[FacultyStudentRow] = []
    for sid, name, email, dept_name, roll in students:
        sid = int(sid)
        reasons: list[str] = []
        score = scores.get(sid)
        if score is None:
            reasons.append(REASON_NO_SCORE)
        elif score[0] is None:
            reasons.append(REASON_NO_EVIDENCE)
        n_high = high_counts.get(sid, 0)
        if n_high >= 1:
            noun = "skill gap" if n_high == 1 else "skill gaps"
            reasons.append(f"{n_high} high-priority {noun}")
        last = last_results.get(sid)
        rows.append(
            FacultyStudentRow(
                student_id=sid, name=str(name), email=str(email),
                department_name=str(dept_name) if dept_name is not None else None,
                roll_number=roll,
                overall=r2(score[0]) if score is not None and score[0] is not None else None,
                level=score[1] if score is not None else None,
                coverage=r2(score[2]) if score is not None else None,
                high_priority_gap_count=n_high,
                last_assessment_percentage=r2(last[0]) if last is not None else None,
                last_assessment_at=last[1] if last is not None else None,
                needs_support=bool(reasons), support_reasons=reasons,
            )
        )
    rows.sort(key=lambda s: (not s.needs_support, s.name.casefold(), s.student_id))

    audit_service.record(
        db, DASHBOARD_FACULTY_READ, "dashboard", user_id=user.id, college_id=college_id
    )
    db.commit()

    return FacultyDashboardResponse(
        generated_at=datetime.now(UTC),
        totals=FacultyTotals(
            assigned_students=len(rows),
            with_readiness_score=len(scores),
            needing_support=sum(1 for s in rows if s.needs_support),
        ),
        students=rows,
        top_gaps=[
            FacultyTopGap(
                skill_id=int(sid), skill_name=str(n), students_affected=int(a),
                high_priority_students=int(h),
            )
            for sid, n, a, h in gap_rows
        ],
        assessment_performance=[
            FacultyAssessmentPerformance(
                assessment_id=int(aid), title=str(t), attempts_submitted=int(n),
                average_percentage=r2(avg) if avg is not None else None,
            )
            for aid, t, n, avg in perf_rows
        ],
    )
