"""Readiness computation, persistence and retrieval (tenant scoped).

Scores come only from the deterministic engine in ``readiness_engine``; this module does the
I/O around it: load evidence and the active rule, persist the result with rule id/version and
evidence, and read stored results back.
"""
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.models import (
    CareerRole,
    GapPriority,
    GapStatus,
    ReadinessRule,
    ReadinessScore,
    RoleSkill,
    Skill,
    SkillCategory,
    SkillGap,
    Student,
    StudentSkill,
    User,
)
from app.schemas.readiness import GapResponse, ReadinessResultResponse
from app.services import (
    audit_service,
    career_role_service,
    readiness_engine,
    readiness_rule_service,
)
from app.services import student_service as student_svc
from app.services.readiness_engine import (
    LevelThreshold,
    RoleRequirement,
    RuleConfig,
    SkillEvidence,
)

STAFF_READ = "READINESS_READ"
COMPUTE = "READINESS_COMPUTE"


def _rule_config(rule: ReadinessRule) -> RuleConfig:
    return RuleConfig(
        rule_id=rule.id,
        version=rule.version,
        weights={int(k): float(v) for k, v in rule.weights.items()},
        level_thresholds=[
            LevelThreshold(level=str(t["level"]), min_score=float(t["min_score"]))
            for t in rule.level_thresholds
        ],
        high_min_gap=float(rule.gap_thresholds["high_min_gap"]),
        medium_min_gap=float(rule.gap_thresholds["medium_min_gap"]),
    )


def _load_evidence(db: Session, student: Student) -> list[SkillEvidence]:
    stmt = (
        select(StudentSkill, Skill.name, SkillCategory.id, SkillCategory.name)
        .join(Skill, Skill.id == StudentSkill.skill_id)
        .join(SkillCategory, SkillCategory.id == Skill.category_id)
        .where(
            StudentSkill.student_id == student.id,
            StudentSkill.college_id == student.college_id,
            Skill.college_id == student.college_id,
            SkillCategory.college_id == student.college_id,
        )
    )
    return [
        SkillEvidence(
            skill_id=ss.skill_id,
            skill_name=sname,
            category_id=cid,
            category_name=cname,
            score=float(ss.score),
            evidence_count=ss.evidence_count,
            last_result_id=ss.last_result_id,
        )
        for ss, sname, cid, cname in db.execute(stmt).all()
    ]


def _load_requirements(db: Session, college_id: int, role_id: int) -> list[RoleRequirement]:
    stmt = (
        select(RoleSkill, Skill.name, SkillCategory.id, SkillCategory.name)
        .join(Skill, Skill.id == RoleSkill.skill_id)
        .join(SkillCategory, SkillCategory.id == Skill.category_id)
        .where(
            RoleSkill.role_id == role_id,
            RoleSkill.college_id == college_id,
            Skill.college_id == college_id,
            SkillCategory.college_id == college_id,
        )
    )
    return [
        RoleRequirement(
            skill_id=rs.skill_id,
            skill_name=sname,
            category_id=cid,
            category_name=cname,
            required_level=float(rs.required_level),
            weight=float(rs.weight),
        )
        for rs, sname, cid, cname in db.execute(stmt).all()
    ]


def _category_names(db: Session, college_id: int, ids: list[int]) -> dict[int, str]:
    rows = db.execute(
        select(SkillCategory.id, SkillCategory.name).where(
            SkillCategory.college_id == college_id, SkillCategory.id.in_(ids)
        )
    ).all()
    return {int(i): str(n) for i, n in rows}


def compute(
    db: Session, user: User, student: Student, role_id: int | None
) -> ReadinessResultResponse:
    """Compute and persist readiness (general, or for a role) for the student.

    Raises ConflictError when the college has no active rule and NotFoundError when the role is
    not an active, visible role of the student's college.
    """
    rule = readiness_rule_service.get_active_rule(db, student.college_id)
    if rule is None:
        raise ConflictError("No active readiness rule configured")
    role: CareerRole | None = None
    if role_id is not None:
        role = career_role_service.get_visible_role(db, student, role_id)
    config = _rule_config(rule)
    skills = _load_evidence(db, student)
    if role is None:
        names = _category_names(db, student.college_id, list(config.weights))
        result = readiness_engine.compute_general(config, skills, names)
    else:
        reqs = _load_requirements(db, student.college_id, role.id)
        result = readiness_engine.compute_role(config, reqs, skills)

    now = datetime.now(UTC)
    score = ReadinessScore(
        student_id=student.id,
        college_id=student.college_id,
        role_id=role.id if role is not None else None,
        rule_id=rule.id,
        rule_version=rule.version,
        overall=result.overall,
        level=result.level,
        coverage=result.coverage,
        category_scores=[
            {
                "category_id": c.category_id,
                "category_name": c.category_name,
                "weight": c.weight,
                "score": c.score,
                "evidence_count": c.evidence_count,
            }
            for c in result.category_scores
        ],
        evidence=[
            {
                "skill_id": e.skill_id,
                "skill_name": e.skill_name,
                "category_name": e.category_name,
                "score": e.score,
                "evidence_count": e.evidence_count,
                "last_result_id": e.last_result_id,
            }
            for e in result.evidence
        ],
        computed_at=now,
    )
    db.add(score)
    db.flush()
    if role is not None:
        for gap in result.gaps:
            db.add(
                SkillGap(
                    student_id=student.id,
                    college_id=student.college_id,
                    role_id=role.id,
                    skill_id=gap.skill_id,
                    readiness_score_id=score.id,
                    current=gap.current,
                    required=gap.required,
                    gap=gap.gap,
                    status=GapStatus(gap.status),
                    priority=GapPriority(gap.priority),
                    recommended_action=gap.recommended_action,
                    computed_at=now,
                )
            )
    audit_service.record(
        db,
        COMPUTE,
        "readiness_score",
        user_id=user.id,
        college_id=user.college_id,
        resource_id=score.id,
        metadata={"rule_id": rule.id, "rule_version": rule.version, "role_id": score.role_id},
    )
    db.commit()
    return to_result(db, score, include_gaps=True)


def _gaps_for(db: Session, score: ReadinessScore) -> list[GapResponse]:
    stmt = (
        select(SkillGap, Skill.name)
        .join(Skill, Skill.id == SkillGap.skill_id)
        .where(
            SkillGap.readiness_score_id == score.id,
            SkillGap.college_id == score.college_id,
            Skill.college_id == score.college_id,
        )
        .order_by(SkillGap.id)
    )
    return [
        GapResponse(
            skill_id=g.skill_id,
            skill_name=name,
            current=float(g.current) if g.current is not None else None,
            required=float(g.required),
            gap=float(g.gap) if g.gap is not None else None,
            status=g.status,
            priority=g.priority,
            recommended_action=g.recommended_action,
        )
        for g, name in db.execute(stmt).all()
    ]


def to_result(db: Session, score: ReadinessScore, include_gaps: bool) -> ReadinessResultResponse:
    """Build the API result from a stored score (and its gap rows)."""
    role_name: str | None = None
    if score.role_id is not None:
        role_name = db.execute(
            select(CareerRole.name).where(
                CareerRole.id == score.role_id, CareerRole.college_id == score.college_id
            )
        ).scalar_one_or_none()
    payload: dict[str, Any] = {
        "id": score.id,
        "student_id": score.student_id,
        "role_id": score.role_id,
        "role_name": role_name,
        "rule_id": score.rule_id,
        "rule_version": score.rule_version,
        "overall": float(score.overall) if score.overall is not None else None,
        "level": score.level,
        "coverage": float(score.coverage),
        "category_scores": score.category_scores,
        "evidence": score.evidence,
        "gaps": [],
        "computed_at": score.computed_at,
    }
    result = ReadinessResultResponse.model_validate(payload)
    if include_gaps and score.role_id is not None:
        result.gaps = _gaps_for(db, score)
    return result


def _scores_stmt(student: Student, role_id: int | None) -> Any:
    stmt = select(ReadinessScore).where(
        ReadinessScore.student_id == student.id,
        ReadinessScore.college_id == student.college_id,
    )
    if role_id is None:
        stmt = stmt.where(ReadinessScore.role_id.is_(None))
    else:
        stmt = stmt.where(ReadinessScore.role_id == role_id)
    return stmt.order_by(ReadinessScore.computed_at.desc(), ReadinessScore.id.desc())


def latest_score(db: Session, student: Student, role_id: int | None) -> ReadinessScore:
    """Latest stored score or NotFoundError."""
    score = db.execute(_scores_stmt(student, role_id).limit(1)).scalar_one_or_none()
    if score is None:
        raise NotFoundError("Readiness has not been computed")
    return score


def latest_result(db: Session, student: Student, role_id: int | None) -> ReadinessResultResponse:
    """Latest stored result (with gaps for role scores)."""
    return to_result(db, latest_score(db, student, role_id), include_gaps=True)


def history(db: Session, student: Student, role_id: int | None) -> list[ReadinessResultResponse]:
    """All stored results, newest first (gaps omitted)."""
    scores = db.execute(_scores_stmt(student, role_id)).scalars()
    return [to_result(db, s, include_gaps=False) for s in scores]


def latest_gaps(db: Session, student: Student, role_id: int) -> list[GapResponse]:
    """Gaps of the latest stored role score."""
    return _gaps_for(db, latest_score(db, student, role_id))


def staff_read(
    db: Session, caller: User, student_id: int, role_id: int | None
) -> ReadinessResultResponse:
    """Latest result for a student under the same access rules as GET /students/{id}."""
    student = student_svc.get_accessible_student(db, caller, student_id)
    result = latest_result(db, student, role_id)
    if student.user_id != caller.id:
        audit_service.record(
            db,
            STAFF_READ,
            "readiness_score",
            user_id=caller.id,
            college_id=caller.college_id,
            resource_id=result.id,
            metadata={"student_id": student.id, "role_id": role_id},
        )
        db.commit()
    return result
