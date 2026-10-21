"""Student dashboard aggregation (read-only, tenant scoped, stored data only)."""
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentResult,
    AttemptStatus,
    CareerRole,
    GapPriority,
    InterviewResult,
    ReadinessScore,
    Resume,
    ResumeAnalysis,
    Skill,
    SkillCategory,
    Student,
    StudentSkill,
    User,
)
from app.schemas.readiness import GapResponse
from app.schemas.student_dashboard import (
    DashboardAssessment,
    DashboardGap,
    DashboardGoal,
    DashboardInterview,
    DashboardInterviewLatest,
    DashboardPlan,
    DashboardProfile,
    DashboardReadiness,
    DashboardReadinessBlock,
    DashboardResume,
    DashboardRoleReadiness,
    DashboardSkill,
    StudentDashboardResponse,
)
from app.services import (
    career_goal_service,
    learning_plan_service,
    readiness_rule_service,
    readiness_service,
    student_service,
)

MAX_GAPS = 5
MAX_ASSESSMENTS = 5
NOT_IMPLEMENTED: list[str] = []
_MATCH_KEYS = ("match_percent", "percent", "match_percentage", "score")
_PRIORITY_ORDER = {
    GapPriority.HIGH: 0,
    GapPriority.MEDIUM: 1,
    GapPriority.LOW: 2,
    GapPriority.UNASSESSED: 3,
    GapPriority.NONE: 4,
}


def _scores(db: Session, student: Student) -> list[ReadinessScore]:
    """All stored scores, newest first (one query)."""
    return list(
        db.execute(
            select(ReadinessScore)
            .where(
                ReadinessScore.student_id == student.id,
                ReadinessScore.college_id == student.college_id,
            )
            .order_by(ReadinessScore.computed_at.desc(), ReadinessScore.id.desc())
        ).scalars()
    )


def _summary(score: ReadinessScore) -> DashboardReadiness:
    return DashboardReadiness(
        overall=float(score.overall) if score.overall is not None else None,
        level=score.level,
        coverage=float(score.coverage),
        rule_version=score.rule_version,
        computed_at=score.computed_at,
    )


def _role_names(db: Session, college_id: int, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = db.execute(
        select(CareerRole.id, CareerRole.name).where(
            CareerRole.college_id == college_id, CareerRole.id.in_(ids)
        )
    ).all()
    return {int(i): str(n) for i, n in rows}


def _skills(db: Session, student: Student) -> list[DashboardSkill]:
    stmt = (
        select(StudentSkill, Skill.name, SkillCategory.name)
        .join(Skill, Skill.id == StudentSkill.skill_id)
        .join(SkillCategory, SkillCategory.id == Skill.category_id)
        .where(
            StudentSkill.student_id == student.id,
            StudentSkill.college_id == student.college_id,
            Skill.college_id == student.college_id,
            SkillCategory.college_id == student.college_id,
        )
        .order_by(StudentSkill.score.desc(), Skill.name)
    )
    return [
        DashboardSkill(
            skill_id=ss.skill_id,
            skill_name=sname,
            category_name=cname,
            score=float(ss.score),
            evidence_count=ss.evidence_count,
        )
        for ss, sname, cname in db.execute(stmt).all()
    ]


def _gap_sort_key(g: GapResponse) -> tuple[int, float]:
    return (_PRIORITY_ORDER[g.priority], -(g.gap if g.gap is not None else 0.0))


def _top_gaps(
    db: Session,
    latest_by_role: dict[int, ReadinessScore],
    plan_role_id: int | None,
    goal_role_ids: list[int],
    names: dict[int, str],
) -> list[DashboardGap]:
    candidates = [plan_role_id] if plan_role_id is not None else goal_role_ids
    for role_id in candidates:
        score = latest_by_role.get(role_id)
        if score is None:
            continue
        gaps = readiness_service._gaps_for(db, score)
        if not gaps:
            continue
        gaps.sort(key=_gap_sort_key)
        return [
            DashboardGap(
                role_id=role_id,
                role_name=names.get(role_id),
                skill_id=g.skill_id,
                skill_name=g.skill_name,
                current=g.current,
                required=g.required,
                gap=g.gap,
                status=g.status,
                priority=g.priority,
                recommended_action=g.recommended_action,
            )
            for g in gaps[:MAX_GAPS]
        ]
    return []


def _recent_assessments(db: Session, student: Student) -> list[DashboardAssessment]:
    stmt = (
        select(
            AssessmentAttempt.id,
            Assessment.title,
            AssessmentResult.percentage,
            AssessmentAttempt.submitted_at,
        )
        .join(Assessment, Assessment.id == AssessmentAttempt.assessment_id)
        .join(AssessmentResult, AssessmentResult.attempt_id == AssessmentAttempt.id)
        .where(
            AssessmentAttempt.student_id == student.id,
            AssessmentAttempt.college_id == student.college_id,
            AssessmentAttempt.status == AttemptStatus.SUBMITTED,
            Assessment.college_id == student.college_id,
            AssessmentResult.college_id == student.college_id,
        )
        .order_by(AssessmentAttempt.submitted_at.desc(), AssessmentAttempt.id.desc())
        .limit(MAX_ASSESSMENTS)
    )
    return [
        DashboardAssessment(
            attempt_id=aid, assessment_title=title, percentage=float(pct), submitted_at=sub
        )
        for aid, title, pct, sub in db.execute(stmt).all()
    ]


def _match_percent(role_match: dict[str, Any] | None) -> float | None:
    if not isinstance(role_match, dict):
        return None
    for key in _MATCH_KEYS:
        val = role_match.get(key)
        if isinstance(val, int | float) and not isinstance(val, bool):
            return float(val)
    return None


def _latest_resume(db: Session, student: Student) -> DashboardResume | None:
    """Most recent resume analysis of the student; None when absent or the feature is missing."""
    stmt = (
        select(ResumeAnalysis, Resume.original_filename)
        .join(Resume, Resume.id == ResumeAnalysis.resume_id)
        .where(
            ResumeAnalysis.student_id == student.id,
            ResumeAnalysis.college_id == student.college_id,
            Resume.college_id == student.college_id,
            Resume.student_id == student.id,
        )
        .order_by(ResumeAnalysis.created_at.desc(), ResumeAnalysis.id.desc())
        .limit(1)
    )
    try:
        row = db.execute(stmt).first()
    except (OperationalError, ProgrammingError):
        db.rollback()
        return None
    if row is None:
        return None
    analysis, filename = row
    names = (
        _role_names(db, student.college_id, {analysis.role_id})
        if analysis.role_id is not None
        else {}
    )
    return DashboardResume(
        resume_id=analysis.resume_id,
        filename=filename,
        analyzed_at=analysis.created_at,
        role_name=names.get(analysis.role_id) if analysis.role_id is not None else None,
        role_match_percent=_match_percent(analysis.role_match),
    )


def _interview_block(db: Session, student: Student) -> DashboardInterview:
    """Completed mock interview count and the latest stored result."""
    try:
        count = db.execute(
            select(func.count(InterviewResult.id)).where(
                InterviewResult.student_id == student.id,
                InterviewResult.college_id == student.college_id,
            )
        ).scalar_one()
        latest_row = db.execute(
            select(InterviewResult.role_id, InterviewResult.overall, InterviewResult.computed_at)
            .where(
                InterviewResult.student_id == student.id,
                InterviewResult.college_id == student.college_id,
            )
            .order_by(InterviewResult.computed_at.desc(), InterviewResult.id.desc())
            .limit(1)
        ).first()
    except (OperationalError, ProgrammingError):
        db.rollback()
        return DashboardInterview(completed_count=0, latest=None)
    if latest_row is None:
        return DashboardInterview(completed_count=int(count), latest=None)
    role_id, overall, computed_at = latest_row
    names = _role_names(db, student.college_id, {role_id})
    return DashboardInterview(
        completed_count=int(count),
        latest=DashboardInterviewLatest(
            role_name=names.get(role_id),
            overall=float(overall) if overall is not None else None,
            computed_at=computed_at,
        ),
    )


def build(db: Session, user: User) -> StudentDashboardResponse:
    """Assemble the dashboard for the calling student."""
    student = student_service.get_or_create_me(db, user)
    profile = student_service.to_response(db, student)
    goals = career_goal_service.list_goals(db, student)
    plan = learning_plan_service._active_plan(db, student)
    scores = _scores(db, student)

    general: ReadinessScore | None = None
    latest_by_role: dict[int, ReadinessScore] = {}
    for s in scores:  # newest first: first seen per key is the latest
        if s.role_id is None:
            general = general or s
        else:
            latest_by_role.setdefault(s.role_id, s)

    role_ids = set(latest_by_role)
    if plan is not None:
        role_ids.add(plan.role_id)
    names = _role_names(db, student.college_id, role_ids)

    plan_out: DashboardPlan | None = None
    if plan is not None:
        plan_out = DashboardPlan(
            id=plan.id,
            role_id=plan.role_id,
            role_name=names.get(plan.role_id),
            status=plan.status.value,
            starts_on=plan.starts_on,
            progress=learning_plan_service._progress_for(db, plan.college_id, [plan.id])[plan.id],
        )

    return StudentDashboardResponse(
        profile=DashboardProfile(
            profile_complete=profile.profile_complete,
            department_name=profile.department_name,
            roll_number=profile.roll_number,
        ),
        rule_active=readiness_rule_service.get_active_rule(db, student.college_id) is not None,
        readiness=DashboardReadinessBlock(
            general=_summary(general) if general is not None else None,
            roles=[
                DashboardRoleReadiness(
                    role_id=rid, role_name=names.get(rid), **_summary(s).model_dump()
                )
                for rid, s in latest_by_role.items()
            ],
        ),
        skills=_skills(db, student),
        top_gaps=_top_gaps(
            db,
            latest_by_role,
            plan.role_id if plan is not None else None,
            [g.career_role_id for g in goals],
            names,
        ),
        goals=[
            DashboardGoal(
                career_role_id=g.career_role_id, role_name=g.role_name, priority=g.priority
            )
            for g in goals
        ],
        plan=plan_out,
        recent_assessments=_recent_assessments(db, student),
        resume=_latest_resume(db, student),
        interview=_interview_block(db, student),
        not_implemented=list(NOT_IMPLEMENTED),
    )
