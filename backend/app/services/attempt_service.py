"""Student-facing assessment flow: listing, attempts, answers, submission, results.

Answer keys (``correct_option_ids``) never leave this module; only scoring reads them.
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentQuestion,
    AssessmentResult,
    AssessmentStatus,
    AttemptStatus,
    Skill,
    Student,
    StudentSkill,
)
from app.schemas.assessment import (
    AssessmentSummary,
    AttemptQuestion,
    AttemptResponse,
    HistoryItem,
    Option,
    ResultResponse,
    SkillScoreResponse,
    StudentAssessmentSummary,
)
from app.services import assessment_service, audit_service
from app.services.scoring import QuestionSpec, ScoreOutcome, score_attempt


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; treat them as UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def expires_at(attempt: AssessmentAttempt, assessment: Assessment) -> datetime | None:
    """Deadline of an attempt, or None when the assessment has no time limit."""
    if assessment.time_limit_min is None:
        return None
    return _aware(attempt.started_at) + timedelta(minutes=assessment.time_limit_min)


def _is_expired(attempt: AssessmentAttempt, assessment: Assessment) -> bool:
    deadline = expires_at(attempt, assessment)
    return deadline is not None and _now() > deadline


# ---- visibility -----------------------------------------------------------------------------
def _visible_stmt(student: Student) -> Select[tuple[Assessment]]:
    return select(Assessment).where(
        Assessment.college_id == student.college_id,
        Assessment.status == AssessmentStatus.PUBLISHED,
        or_(Assessment.department_id.is_(None), Assessment.department_id == student.department_id),
    )


def _get_visible(db: Session, student: Student, assessment_id: int) -> Assessment:
    stmt = _visible_stmt(student).where(Assessment.id == assessment_id)
    a = db.execute(stmt).scalar_one_or_none()
    if a is None:
        raise NotFoundError("Assessment not found")
    return a


def list_for_student(db: Session, student: Student) -> list[StudentAssessmentSummary]:
    """Visible PUBLISHED assessments with the student's attempt state."""
    rows = list(db.execute(_visible_stmt(student).order_by(Assessment.id.desc())).scalars())
    stats = assessment_service.question_stats(db, student.college_id, [r.id for r in rows])
    attempts = list(
        db.execute(
            select(AssessmentAttempt).where(
                AssessmentAttempt.student_id == student.id,
                AssessmentAttempt.college_id == student.college_id,
                AssessmentAttempt.assessment_id.in_([r.id for r in rows]),
            )
        ).scalars()
    )
    out: list[StudentAssessmentSummary] = []
    for r in rows:
        mine = [x for x in attempts if x.assessment_id == r.id]
        live = [x for x in mine if x.status == AttemptStatus.IN_PROGRESS and not _is_expired(x, r)]
        out.append(
            StudentAssessmentSummary(
                **assessment_service.summary_fields(r, stats),  # type: ignore[arg-type]
                attempts_used=len(mine),
                in_progress_attempt_id=live[0].id if live else None,
            )
        )
    return out


def get_for_student(db: Session, student: Student, assessment_id: int) -> AssessmentSummary:
    """Summary of a visible assessment (no questions)."""
    a = _get_visible(db, student, assessment_id)
    return assessment_service.to_summary(db, a)


# ---- attempts -------------------------------------------------------------------------------
def _load_questions(db: Session, college_id: int, assessment_id: int) -> list[AssessmentQuestion]:
    return list(
        db.execute(
            select(AssessmentQuestion)
            .where(
                AssessmentQuestion.assessment_id == assessment_id,
                AssessmentQuestion.college_id == college_id,
            )
            .order_by(AssessmentQuestion.position, AssessmentQuestion.id)
        ).scalars()
    )


def _skill_names(db: Session, college_id: int, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = db.execute(
        select(Skill.id, Skill.name).where(Skill.college_id == college_id, Skill.id.in_(ids))
    ).all()
    return {sid: name for sid, name in rows}


def build_attempt_response(
    db: Session, attempt: AssessmentAttempt, assessment: Assessment
) -> AttemptResponse:
    """Attempt payload with questions stripped of answer keys."""
    questions = _load_questions(db, attempt.college_id, assessment.id)
    names = _skill_names(db, attempt.college_id, {q.skill_id for q in questions})
    return AttemptResponse(
        id=attempt.id,
        assessment_id=assessment.id,
        attempt_no=attempt.attempt_no,
        status=attempt.status.value,
        started_at=_aware(attempt.started_at),
        expires_at=expires_at(attempt, assessment),
        questions=[
            AttemptQuestion(
                id=q.id,
                body=q.body,
                options=[Option(**o) for o in q.options],
                marks=float(q.marks),
                position=q.position,
                skill_id=q.skill_id,
                skill_name=names.get(q.skill_id, ""),
                multi_select=len(set(q.correct_option_ids)) > 1,
            )
            for q in questions
        ],
        answers={k: list(v) for k, v in (attempt.answers or {}).items()},
    )


def _attempts_of(db: Session, student: Student, assessment_id: int) -> list[AssessmentAttempt]:
    return list(
        db.execute(
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.student_id == student.id,
                AssessmentAttempt.college_id == student.college_id,
            )
            .order_by(AssessmentAttempt.attempt_no)
        ).scalars()
    )


def start_attempt(
    db: Session, user_id: int, student: Student, assessment_id: int
) -> tuple[AttemptResponse, bool]:
    """Start (or resume) an attempt. Returns (attempt, created)."""
    a = _get_visible(db, student, assessment_id)
    existing = _attempts_of(db, student, a.id)
    for att in existing:
        if att.status != AttemptStatus.IN_PROGRESS:
            continue
        if not _is_expired(att, a):
            return build_attempt_response(db, att, a), False
        # A stale attempt past its deadline is finalised as EXPIRED before counting attempts.
        finalize(db, user_id, student, att, a)
    existing = _attempts_of(db, student, a.id)
    if a.max_attempts is not None and len(existing) >= a.max_attempts:
        raise ConflictError("Maximum attempts reached")
    attempt = AssessmentAttempt(
        assessment_id=a.id,
        student_id=student.id,
        college_id=student.college_id,
        attempt_no=(existing[-1].attempt_no + 1) if existing else 1,
        status=AttemptStatus.IN_PROGRESS,
        started_at=_now(),
        answers={},
    )
    db.add(attempt)
    db.flush()
    audit_service.record(
        db, "ASSESSMENT_ATTEMPT_START", "assessment_attempt",
        user_id=user_id, college_id=student.college_id, resource_id=attempt.id,
        metadata={"assessment_id": a.id, "attempt_no": attempt.attempt_no},
    )
    db.commit()
    return build_attempt_response(db, attempt, a), True


def _get_own_attempt(
    db: Session, student: Student, attempt_id: int
) -> tuple[AssessmentAttempt, Assessment]:
    attempt = db.execute(
        select(AssessmentAttempt).where(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.student_id == student.id,
            AssessmentAttempt.college_id == student.college_id,
        )
    ).scalar_one_or_none()
    if attempt is None:
        raise NotFoundError("Attempt not found")
    assessment = assessment_service.get_assessment(db, student.college_id, attempt.assessment_id)
    return attempt, assessment


def save_answers(
    db: Session, student: Student, attempt_id: int, answers: dict[str, list[str]]
) -> int:
    """Merge answers into an IN_PROGRESS attempt; returns the number of answers saved."""
    attempt, assessment = _get_own_attempt(db, student, attempt_id)
    if attempt.status != AttemptStatus.IN_PROGRESS or _is_expired(attempt, assessment):
        raise ConflictError("Attempt is not in progress")
    questions = {str(q.id): q for q in _load_questions(db, student.college_id, assessment.id)}
    cleaned: dict[str, list[str]] = {}
    for qid, selected in answers.items():
        q = questions.get(qid)
        if q is None:
            raise UnprocessableError(f"Unknown question id {qid}")
        valid = {str(o["id"]) for o in q.options}
        bad = [s for s in selected if s not in valid]
        if bad:
            raise UnprocessableError(f"Unknown option id for question {qid}")
        cleaned[qid] = list(dict.fromkeys(selected))
    merged = dict(attempt.answers or {})
    merged.update(cleaned)
    attempt.answers = merged
    db.commit()
    return len(cleaned)


# ---- submission and results -----------------------------------------------------------------
def _outcome_json(outcome: ScoreOutcome) -> dict[str, dict[str, float]]:
    return {
        str(sid): {
            "score": float(s.score),
            "max": float(s.max),
            "percentage": float(s.percentage),
        }
        for sid, s in outcome.per_skill.items()
    }


def _upsert_student_skills(
    db: Session, student: Student, outcome: ScoreOutcome, result_id: int
) -> None:
    for sid, s in outcome.per_skill.items():
        row = db.execute(
            select(StudentSkill).where(
                StudentSkill.student_id == student.id,
                StudentSkill.skill_id == sid,
                StudentSkill.college_id == student.college_id,
            )
        ).scalar_one_or_none()
        if row is None:
            db.add(
                StudentSkill(
                    student_id=student.id,
                    college_id=student.college_id,
                    skill_id=sid,
                    score=s.percentage,
                    evidence_count=s.question_count,
                    last_result_id=result_id,
                )
            )
        else:
            row.score = s.percentage
            row.evidence_count = row.evidence_count + s.question_count
            row.last_result_id = result_id


def finalize(
    db: Session,
    user_id: int,
    student: Student,
    attempt: AssessmentAttempt,
    assessment: Assessment,
) -> AssessmentResult:
    """Score an IN_PROGRESS attempt, persist the result and update student skills."""
    status = AttemptStatus.EXPIRED if _is_expired(attempt, assessment) else AttemptStatus.SUBMITTED
    questions = _load_questions(db, student.college_id, assessment.id)
    specs = [
        QuestionSpec(
            id=q.id,
            skill_id=q.skill_id,
            marks=Decimal(str(q.marks)),
            correct_option_ids=frozenset(str(c) for c in q.correct_option_ids),
        )
        for q in questions
    ]
    outcome = score_attempt(specs, attempt.answers or {}, Decimal(str(assessment.negative_marking)))
    attempt.status = status
    attempt.submitted_at = _now()
    result = AssessmentResult(
        attempt_id=attempt.id,
        college_id=student.college_id,
        student_id=student.id,
        assessment_id=assessment.id,
        assessment_version=assessment.version,
        total_score=outcome.total_score,
        max_score=outcome.max_score,
        percentage=outcome.percentage,
        per_skill_scores=_outcome_json(outcome),
        computed_at=_now(),
    )
    db.add(result)
    db.flush()
    _upsert_student_skills(db, student, outcome, result.id)
    audit_service.record(
        db, "ASSESSMENT_SUBMIT", "assessment_attempt",
        user_id=user_id, college_id=student.college_id, resource_id=attempt.id,
        metadata={"status": status.value, "result_id": result.id},
    )
    db.commit()
    return result


def to_result_response(
    db: Session, result: AssessmentResult, assessment_title: str
) -> ResultResponse:
    """Build a ResultResponse (no answer keys)."""
    raw = result.per_skill_scores or {}
    names = _skill_names(db, result.college_id, {int(k) for k in raw})
    return ResultResponse(
        id=result.id,
        attempt_id=result.attempt_id,
        assessment_id=result.assessment_id,
        assessment_title=assessment_title,
        assessment_version=result.assessment_version,
        total_score=float(result.total_score),
        max_score=float(result.max_score),
        percentage=float(result.percentage),
        per_skill_scores=[
            SkillScoreResponse(
                skill_id=int(k),
                skill_name=names.get(int(k), ""),
                score=float(v["score"]),
                max=float(v["max"]),
                percentage=float(v["percentage"]),
            )
            for k, v in raw.items()
        ],
        computed_at=_aware(result.computed_at),
    )


def _result_of(db: Session, college_id: int, attempt_id: int) -> AssessmentResult | None:
    return db.execute(
        select(AssessmentResult).where(
            AssessmentResult.attempt_id == attempt_id, AssessmentResult.college_id == college_id
        )
    ).scalar_one_or_none()


def submit(db: Session, user_id: int, student: Student, attempt_id: int) -> ResultResponse:
    """Submit an attempt (idempotent)."""
    attempt, assessment = _get_own_attempt(db, student, attempt_id)
    result = _result_of(db, student.college_id, attempt.id)
    if result is None:
        result = finalize(db, user_id, student, attempt, assessment)
    return to_result_response(db, result, assessment.title)


def get_result(db: Session, student: Student, attempt_id: int) -> ResultResponse:
    """Result of an own, finished attempt."""
    attempt, assessment = _get_own_attempt(db, student, attempt_id)
    result = _result_of(db, student.college_id, attempt.id)
    if result is None:
        raise NotFoundError("Result not available")
    return to_result_response(db, result, assessment.title)


def history(db: Session, student: Student) -> list[HistoryItem]:
    """Own results, newest first."""
    stmt = (
        select(AssessmentResult, AssessmentAttempt, Assessment.title)
        .join(AssessmentAttempt, AssessmentAttempt.id == AssessmentResult.attempt_id)
        .join(Assessment, Assessment.id == AssessmentResult.assessment_id)
        .where(
            AssessmentResult.student_id == student.id,
            AssessmentResult.college_id == student.college_id,
            AssessmentAttempt.college_id == student.college_id,
            Assessment.college_id == student.college_id,
        )
        .order_by(AssessmentResult.computed_at.desc(), AssessmentResult.id.desc())
    )
    items: list[HistoryItem] = []
    for result, attempt, title in db.execute(stmt).all():
        base = to_result_response(db, result, title)
        items.append(
            HistoryItem(
                **base.model_dump(),
                submitted_at=_aware(attempt.submitted_at) if attempt.submitted_at else None,
                attempt_no=attempt.attempt_no,
            )
        )
    return items
