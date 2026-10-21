"""Interview question bank authoring (tenant scoped, soft delete)."""
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, UnprocessableError
from app.models import CareerRole, InterviewQuestion, Skill
from app.schemas.interview import (
    InterviewQuestionAdmin,
    InterviewQuestionCreate,
    InterviewQuestionUpdate,
    RubricConcept,
)
from app.services import audit_service


def _check_refs(db: Session, college_id: int, role_id: int | None, skill_id: int | None) -> None:
    if role_id is not None and (
        db.execute(
            select(CareerRole.id).where(
                CareerRole.id == role_id, CareerRole.college_id == college_id
            )
        ).first()
        is None
    ):
        raise UnprocessableError("Career role not found")
    if skill_id is not None and (
        db.execute(
            select(Skill.id).where(Skill.id == skill_id, Skill.college_id == college_id)
        ).first()
        is None
    ):
        raise UnprocessableError("Skill not found")


def _rubric_json(rubric: list[RubricConcept]) -> list[dict[str, Any]]:
    return [r.model_dump() for r in rubric]


def get_question(db: Session, college_id: int, question_id: int) -> InterviewQuestion:
    """Question of the college or NotFoundError."""
    q = db.execute(
        select(InterviewQuestion).where(
            InterviewQuestion.id == question_id, InterviewQuestion.college_id == college_id
        )
    ).scalar_one_or_none()
    if q is None:
        raise NotFoundError("Interview question not found")
    return q


def _role_names(db: Session, college_id: int) -> dict[int, str]:
    rows = db.execute(
        select(CareerRole.id, CareerRole.name).where(CareerRole.college_id == college_id)
    ).all()
    return {int(i): str(n) for i, n in rows}


def to_admin(q: InterviewQuestion, names: dict[int, str]) -> InterviewQuestionAdmin:
    """Serialize a question for staff."""
    return InterviewQuestionAdmin(
        id=q.id,
        role_id=q.role_id,
        role_name=names.get(q.role_id) if q.role_id is not None else None,
        skill_id=q.skill_id,
        competency=q.competency,
        prompt=q.prompt,
        rubric=[dict(r) for r in q.rubric],
        min_words=q.min_words,
        is_active=q.is_active,
        created_by=q.created_by,
    )


def list_questions(
    db: Session, college_id: int, role_id: int | None, active: bool | None
) -> list[InterviewQuestionAdmin]:
    """Questions of the college, optionally filtered."""
    stmt = select(InterviewQuestion).where(InterviewQuestion.college_id == college_id)
    if role_id is not None:
        stmt = stmt.where(InterviewQuestion.role_id == role_id)
    if active is not None:
        stmt = stmt.where(InterviewQuestion.is_active == active)
    names = _role_names(db, college_id)
    rows = db.execute(stmt.order_by(InterviewQuestion.id)).scalars()
    return [to_admin(q, names) for q in rows]


def create(
    db: Session, college_id: int, actor_id: int, data: InterviewQuestionCreate
) -> InterviewQuestionAdmin:
    """Create a question."""
    _check_refs(db, college_id, data.role_id, data.skill_id)
    q = InterviewQuestion(
        college_id=college_id,
        role_id=data.role_id,
        skill_id=data.skill_id,
        competency=data.competency,
        prompt=data.prompt,
        rubric=_rubric_json(data.rubric),
        min_words=data.min_words,
        is_active=True,
        created_by=actor_id,
    )
    db.add(q)
    db.flush()
    audit_service.record(
        db, "INTERVIEW_QUESTION_CREATE", "interview_question",
        user_id=actor_id, college_id=college_id, resource_id=q.id,
    )
    db.commit()
    return to_admin(q, _role_names(db, college_id))


def update(
    db: Session, college_id: int, actor_id: int, question_id: int, data: InterviewQuestionUpdate
) -> InterviewQuestionAdmin:
    """Update a question."""
    q = get_question(db, college_id, question_id)
    sent = data.model_fields_set
    new_role = data.role_id if "role_id" in sent else q.role_id
    new_skill = data.skill_id if "skill_id" in sent else q.skill_id
    _check_refs(db, college_id, new_role, new_skill)
    q.role_id, q.skill_id = new_role, new_skill
    if data.competency is not None:
        q.competency = data.competency
    if data.prompt is not None:
        q.prompt = data.prompt
    if data.rubric is not None:
        q.rubric = _rubric_json(data.rubric)
    if data.min_words is not None:
        q.min_words = data.min_words
    if data.is_active is not None:
        q.is_active = data.is_active
    audit_service.record(
        db, "INTERVIEW_QUESTION_UPDATE", "interview_question",
        user_id=actor_id, college_id=college_id, resource_id=q.id,
    )
    db.commit()
    return to_admin(q, _role_names(db, college_id))


def soft_delete(db: Session, college_id: int, actor_id: int, question_id: int) -> None:
    """Deactivate a question (never hard-deleted; old interviews keep working)."""
    q = get_question(db, college_id, question_id)
    q.is_active = False
    audit_service.record(
        db, "INTERVIEW_QUESTION_DELETE", "interview_question",
        user_id=actor_id, college_id=college_id, resource_id=q.id,
    )
    db.commit()
