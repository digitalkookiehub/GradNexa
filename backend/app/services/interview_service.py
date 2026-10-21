"""Mock interview lifecycle: start/resume, save answers, finish (deterministic scoring)."""
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models import (
    CareerRole,
    InterviewAnswer,
    InterviewQuestion,
    InterviewResult,
    InterviewStatus,
    MockInterview,
    Student,
)
from app.schemas.interview import (
    AnswerIn,
    CompetencyScoreOut,
    InterviewListItem,
    InterviewQuestionOut,
    InterviewResponse,
    InterviewResultResponse,
    PerQuestionOut,
)
from app.services import audit_service, career_role_service
from app.services.interview_scoring import (
    DISCLAIMER,
    SCORING_VERSION,
    Concept,
    QuestionInput,
    score_interview,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _role_name(db: Session, college_id: int, role_id: int) -> str | None:
    return db.execute(
        select(CareerRole.name).where(CareerRole.id == role_id, CareerRole.college_id == college_id)
    ).scalar_one_or_none()


def _get_own(db: Session, student: Student, interview_id: int) -> MockInterview:
    iv = db.execute(
        select(MockInterview).where(
            MockInterview.id == interview_id,
            MockInterview.student_id == student.id,
            MockInterview.college_id == student.college_id,
        )
    ).scalar_one_or_none()
    if iv is None:
        raise NotFoundError("Interview not found")
    return iv


def _answers_with_questions(
    db: Session, iv: MockInterview
) -> list[tuple[InterviewAnswer, InterviewQuestion]]:
    rows = db.execute(
        select(InterviewAnswer, InterviewQuestion)
        .join(InterviewQuestion, InterviewQuestion.id == InterviewAnswer.question_id)
        .where(
            InterviewAnswer.interview_id == iv.id,
            InterviewAnswer.college_id == iv.college_id,
            InterviewQuestion.college_id == iv.college_id,
        )
        .order_by(InterviewAnswer.position)
    ).all()
    return [(a, q) for a, q in rows]


def build_interview(db: Session, iv: MockInterview) -> InterviewResponse:
    """Serialize an interview for its student (no rubric, no keywords)."""
    return InterviewResponse(
        id=iv.id,
        role_id=iv.role_id,
        role_name=_role_name(db, iv.college_id, iv.role_id),
        status=iv.status,
        started_at=iv.started_at,
        completed_at=iv.completed_at,
        questions=[
            InterviewQuestionOut(
                answer_id=a.id,
                question_id=q.id,
                position=a.position,
                competency=q.competency,
                prompt=q.prompt,
                min_words=q.min_words,
                answer_text=a.answer_text,
            )
            for a, q in _answers_with_questions(db, iv)
        ],
    )


def _pick_questions(
    db: Session, college_id: int, role_id: int, count: int
) -> list[InterviewQuestion]:
    base = select(InterviewQuestion).where(
        InterviewQuestion.college_id == college_id, InterviewQuestion.is_active.is_(True)
    )
    role_qs = list(
        db.execute(
            base.where(InterviewQuestion.role_id == role_id).order_by(InterviewQuestion.id)
        ).scalars()
    )
    generic = list(
        db.execute(
            base.where(InterviewQuestion.role_id.is_(None)).order_by(InterviewQuestion.id)
        ).scalars()
    )
    return (role_qs + generic)[:count]


def start(
    db: Session, user_id: int, student: Student, role_id: int, count: int
) -> tuple[InterviewResponse, bool]:
    """Start a new interview or return the student's in-progress one. Returns (iv, created)."""
    role = career_role_service.get_visible_role(db, student, role_id)
    existing = db.execute(
        select(MockInterview)
        .where(
            MockInterview.student_id == student.id,
            MockInterview.college_id == student.college_id,
            MockInterview.role_id == role.id,
            MockInterview.status == InterviewStatus.IN_PROGRESS,
        )
        .order_by(MockInterview.id.desc())
    ).scalars().first()
    if existing is not None:
        return build_interview(db, existing), False
    questions = _pick_questions(db, student.college_id, role.id, count)
    if not questions:
        raise ConflictError("No interview questions configured for this role")
    iv = MockInterview(
        student_id=student.id,
        college_id=student.college_id,
        role_id=role.id,
        status=InterviewStatus.IN_PROGRESS,
        started_at=_now(),
    )
    db.add(iv)
    db.flush()
    for pos, q in enumerate(questions, start=1):
        db.add(
            InterviewAnswer(
                interview_id=iv.id,
                college_id=student.college_id,
                question_id=q.id,
                position=pos,
            )
        )
    audit_service.record(
        db, "INTERVIEW_START", "mock_interview",
        user_id=user_id, college_id=student.college_id, resource_id=iv.id,
        metadata={"role_id": role.id, "question_count": len(questions)},
    )
    db.commit()
    return build_interview(db, iv), True


def get(db: Session, student: Student, interview_id: int) -> InterviewResponse:
    """One of the student's interviews."""
    return build_interview(db, _get_own(db, student, interview_id))


def save_answers(
    db: Session, student: Student, interview_id: int, answers: list[AnswerIn]
) -> int:
    """Save answer texts of an IN_PROGRESS interview; returns the number saved."""
    iv = _get_own(db, student, interview_id)
    if iv.status != InterviewStatus.IN_PROGRESS:
        raise ConflictError("Interview is already completed")
    rows = {
        a.id: a
        for a in db.execute(
            select(InterviewAnswer).where(
                InterviewAnswer.interview_id == iv.id,
                InterviewAnswer.college_id == iv.college_id,
            )
        ).scalars()
    }
    for item in answers:
        if item.answer_id not in rows:
            raise UnprocessableError(f"Unknown answer id {item.answer_id}")
    now = _now()
    for item in answers:
        row = rows[item.answer_id]
        row.answer_text = item.answer_text
        row.answered_at = now
    db.commit()
    return len(answers)


def _stored_result(db: Session, iv: MockInterview) -> InterviewResult | None:
    return db.execute(
        select(InterviewResult).where(
            InterviewResult.interview_id == iv.id, InterviewResult.college_id == iv.college_id
        )
    ).scalar_one_or_none()


def to_result_response(db: Session, res: InterviewResult) -> InterviewResultResponse:
    """Serialize a stored result."""
    return InterviewResultResponse(
        id=res.id,
        interview_id=res.interview_id,
        role_name=_role_name(db, res.college_id, res.role_id),
        overall=float(res.overall) if res.overall is not None else None,
        competency_scores=[CompetencyScoreOut(**c) for c in res.competency_scores],
        per_question=[PerQuestionOut(**p) for p in res.per_question],
        computed_at=res.computed_at,
        scoring_version=res.scoring_version,
        disclaimer=DISCLAIMER,
    )


def _inputs(pairs: list[tuple[InterviewAnswer, InterviewQuestion]]) -> list[QuestionInput]:
    out: list[QuestionInput] = []
    for a, q in pairs:
        rubric = tuple(
            Concept(
                concept=str(r["concept"]),
                keywords=tuple(str(k) for k in r["keywords"]),
                weight=float(r["weight"]),
            )
            for r in q.rubric
        )
        out.append(
            QuestionInput(
                question_id=q.id,
                position=a.position,
                prompt=q.prompt,
                competency=q.competency,
                min_words=q.min_words,
                rubric=rubric,
                answer_text=a.answer_text,
            )
        )
    return out


def finish(
    db: Session, user_id: int, student: Student, interview_id: int
) -> InterviewResultResponse:
    """Score the saved answers and complete the interview (idempotent)."""
    iv = _get_own(db, student, interview_id)
    existing = _stored_result(db, iv)
    if existing is not None:
        return to_result_response(db, existing)
    outcome = score_interview(_inputs(_answers_with_questions(db, iv)))
    comp: list[dict[str, Any]] = [
        {"competency": c.competency, "score": c.score, "max": 100, "questions": c.questions}
        for c in outcome.competencies
    ]
    per_q: list[dict[str, Any]] = [
        {
            "question_id": s.question_id,
            "position": s.position,
            "prompt": s.prompt,
            "competency": s.competency,
            "score": s.score,
            "answered": s.answered,
            "too_short": s.too_short,
            "covered_concepts": s.covered_concepts,
            "missed_concepts": s.missed_concepts,
        }
        for s in outcome.questions
    ]
    now = _now()
    res = InterviewResult(
        interview_id=iv.id,
        college_id=iv.college_id,
        student_id=student.id,
        role_id=iv.role_id,
        overall=outcome.overall,
        competency_scores=comp,
        per_question=per_q,
        scoring_version=SCORING_VERSION,
        computed_at=now,
    )
    db.add(res)
    iv.status = InterviewStatus.COMPLETED
    iv.completed_at = now
    db.flush()
    audit_service.record(
        db, "INTERVIEW_FINISH", "mock_interview",
        user_id=user_id, college_id=iv.college_id, resource_id=iv.id,
        metadata={"overall": outcome.overall, "scoring_version": SCORING_VERSION},
    )
    db.commit()
    return to_result_response(db, res)


def get_result(db: Session, student: Student, interview_id: int) -> InterviewResultResponse:
    """Stored result of a finished interview."""
    iv = _get_own(db, student, interview_id)
    res = _stored_result(db, iv)
    if res is None:
        raise NotFoundError("Interview result not found")
    return to_result_response(db, res)


def list_interviews(db: Session, student: Student) -> list[InterviewListItem]:
    """The student's interviews, newest first."""
    rows = db.execute(
        select(MockInterview, CareerRole.name, InterviewResult.overall)
        .join(CareerRole, CareerRole.id == MockInterview.role_id)
        .outerjoin(InterviewResult, InterviewResult.interview_id == MockInterview.id)
        .where(
            MockInterview.student_id == student.id,
            MockInterview.college_id == student.college_id,
        )
        .order_by(MockInterview.started_at.desc(), MockInterview.id.desc())
    ).all()
    return [
        InterviewListItem(
            id=iv.id,
            role_id=iv.role_id,
            role_name=name,
            status=iv.status,
            started_at=iv.started_at,
            completed_at=iv.completed_at,
            overall=float(overall) if overall is not None else None,
        )
        for iv, name, overall in rows
    ]
