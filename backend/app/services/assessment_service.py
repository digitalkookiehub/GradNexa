"""Assessment authoring: assessments, versions and question bank (tenant scoped)."""
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentQuestion,
    AssessmentStatus,
    Department,
    QuestionDifficulty,
    Skill,
)
from app.schemas.assessment import (
    AdminAssessmentDetail,
    AdminQuestion,
    AssessmentCreate,
    AssessmentSummary,
    AssessmentUpdate,
    Option,
    QuestionCreate,
    QuestionUpdate,
)
from app.services import audit_service


def question_stats(db: Session, college_id: int, ids: list[int]) -> dict[int, tuple[int, Decimal]]:
    """Map assessment id -> (question_count, total_marks)."""
    if not ids:
        return {}
    stmt = (
        select(
            AssessmentQuestion.assessment_id,
            func.count(AssessmentQuestion.id),
            func.coalesce(func.sum(AssessmentQuestion.marks), 0),
        )
        .where(
            AssessmentQuestion.college_id == college_id,
            AssessmentQuestion.assessment_id.in_(ids),
        )
        .group_by(AssessmentQuestion.assessment_id)
    )
    return {aid: (int(c), Decimal(str(m))) for aid, c, m in db.execute(stmt).all()}


def summary_fields(a: Assessment, stats: dict[int, tuple[int, Decimal]]) -> dict[str, object]:
    """Common AssessmentSummary field values."""
    count, marks = stats.get(a.id, (0, Decimal("0")))
    return {
        "id": a.id,
        "series_key": a.series_key,
        "version": a.version,
        "title": a.title,
        "type": a.type,
        "department_id": a.department_id,
        "time_limit_min": a.time_limit_min,
        "max_attempts": a.max_attempts,
        "negative_marking": float(a.negative_marking),
        "status": a.status,
        "question_count": count,
        "total_marks": float(marks),
    }


def to_summary(db: Session, a: Assessment) -> AssessmentSummary:
    """Build an AssessmentSummary."""
    return AssessmentSummary(**summary_fields(a, question_stats(db, a.college_id, [a.id])))  # type: ignore[arg-type]


def get_assessment(db: Session, college_id: int, assessment_id: int) -> Assessment:
    """Fetch an assessment of the college or raise NotFoundError."""
    a = db.execute(
        select(Assessment).where(
            Assessment.id == assessment_id, Assessment.college_id == college_id
        )
    ).scalar_one_or_none()
    if a is None:
        raise NotFoundError("Assessment not found")
    return a


def _require_draft(a: Assessment) -> None:
    if a.status != AssessmentStatus.DRAFT:
        raise ConflictError("Only DRAFT assessments can be modified")


def _check_department(db: Session, college_id: int, department_id: int | None) -> None:
    if department_id is None:
        return
    found = db.execute(
        select(Department.id).where(
            Department.id == department_id, Department.college_id == college_id
        )
    ).first()
    if found is None:
        raise UnprocessableError("Department not found")


def list_assessments(
    db: Session, college_id: int, status: AssessmentStatus | None, type_: str | None
) -> list[AssessmentSummary]:
    """Staff listing with optional status/type filters."""
    stmt = select(Assessment).where(Assessment.college_id == college_id)
    if status is not None:
        stmt = stmt.where(Assessment.status == status)
    if type_ is not None:
        stmt = stmt.where(Assessment.type == type_)
    rows = list(db.execute(stmt.order_by(Assessment.id.desc())).scalars())
    stats = question_stats(db, college_id, [r.id for r in rows])
    return [AssessmentSummary(**summary_fields(r, stats)) for r in rows]  # type: ignore[arg-type]


def to_admin_question(q: AssessmentQuestion, skill_name: str) -> AdminQuestion:
    """Build an AdminQuestion."""
    return AdminQuestion(
        id=q.id,
        assessment_id=q.assessment_id,
        skill_id=q.skill_id,
        skill_name=skill_name,
        difficulty=q.difficulty,
        body=q.body,
        options=[Option(**o) for o in q.options],
        correct_option_ids=[str(c) for c in q.correct_option_ids],
        marks=float(q.marks),
        position=q.position,
    )


def _questions(
    db: Session,
    college_id: int,
    *,
    assessment_id: int | None = None,
    skill_id: int | None = None,
    difficulty: QuestionDifficulty | None = None,
    question_id: int | None = None,
) -> list[AdminQuestion]:
    stmt = (
        select(AssessmentQuestion, Skill.name)
        .join(Skill, Skill.id == AssessmentQuestion.skill_id)
        .where(AssessmentQuestion.college_id == college_id, Skill.college_id == college_id)
    )
    if assessment_id is not None:
        stmt = stmt.where(AssessmentQuestion.assessment_id == assessment_id)
    if skill_id is not None:
        stmt = stmt.where(AssessmentQuestion.skill_id == skill_id)
    if difficulty is not None:
        stmt = stmt.where(AssessmentQuestion.difficulty == difficulty)
    if question_id is not None:
        stmt = stmt.where(AssessmentQuestion.id == question_id)
    stmt = stmt.order_by(AssessmentQuestion.assessment_id, AssessmentQuestion.position,
                         AssessmentQuestion.id)
    return [to_admin_question(q, n) for q, n in db.execute(stmt).all()]


def get_detail(db: Session, college_id: int, assessment_id: int) -> AdminAssessmentDetail:
    """Assessment with questions and answer keys (staff)."""
    a = get_assessment(db, college_id, assessment_id)
    stats = question_stats(db, college_id, [a.id])
    return AdminAssessmentDetail(
        **summary_fields(a, stats),  # type: ignore[arg-type]
        created_by=a.created_by,
        questions=_questions(db, college_id, assessment_id=a.id),
    )


def question_bank(
    db: Session,
    college_id: int,
    skill_id: int | None,
    difficulty: QuestionDifficulty | None,
    assessment_id: int | None,
) -> list[AdminQuestion]:
    """Filtered question bank across the college."""
    return _questions(
        db, college_id, assessment_id=assessment_id, skill_id=skill_id, difficulty=difficulty
    )


def create(db: Session, college_id: int, actor_id: int, data: AssessmentCreate) -> Assessment:
    """Create a DRAFT assessment, version 1, with a new series key."""
    _check_department(db, college_id, data.department_id)
    a = Assessment(
        college_id=college_id,
        series_key=uuid.uuid4().hex,
        version=1,
        title=data.title.strip(),
        type=data.type,
        department_id=data.department_id,
        time_limit_min=data.time_limit_min,
        max_attempts=data.max_attempts,
        negative_marking=data.negative_marking,
        status=AssessmentStatus.DRAFT,
        created_by=actor_id,
    )
    db.add(a)
    db.flush()
    audit_service.record(
        db, "ASSESSMENT_CREATE", "assessment",
        user_id=actor_id, college_id=college_id, resource_id=a.id,
    )
    db.commit()
    return a


def update(
    db: Session, college_id: int, actor_id: int, assessment_id: int, data: AssessmentUpdate
) -> Assessment:
    """Update a DRAFT assessment (only fields sent)."""
    a = get_assessment(db, college_id, assessment_id)
    _require_draft(a)
    fields = data.model_fields_set
    if "department_id" in fields:
        _check_department(db, college_id, data.department_id)
        a.department_id = data.department_id
    if data.title is not None:
        a.title = data.title.strip()
    if data.type is not None:
        a.type = data.type
    if "time_limit_min" in fields:
        a.time_limit_min = data.time_limit_min
    if "max_attempts" in fields:
        a.max_attempts = data.max_attempts
    if data.negative_marking is not None:
        a.negative_marking = data.negative_marking
    audit_service.record(
        db, "ASSESSMENT_UPDATE", "assessment",
        user_id=actor_id, college_id=college_id, resource_id=a.id,
    )
    db.commit()
    return a


def delete(db: Session, college_id: int, actor_id: int, assessment_id: int) -> None:
    """Delete a DRAFT assessment that has no attempts."""
    a = get_assessment(db, college_id, assessment_id)
    _require_draft(a)
    has_attempts = db.execute(
        select(AssessmentAttempt.id).where(
            AssessmentAttempt.assessment_id == a.id, AssessmentAttempt.college_id == college_id
        )
    ).first()
    if has_attempts is not None:
        raise ConflictError("Assessment has attempts and cannot be deleted")
    for q in db.execute(
        select(AssessmentQuestion).where(
            AssessmentQuestion.assessment_id == a.id, AssessmentQuestion.college_id == college_id
        )
    ).scalars():
        db.delete(q)
    db.delete(a)
    audit_service.record(
        db, "ASSESSMENT_DELETE", "assessment",
        user_id=actor_id, college_id=college_id, resource_id=assessment_id,
    )
    db.commit()


def publish(db: Session, college_id: int, actor_id: int, assessment_id: int) -> Assessment:
    """Publish a DRAFT with at least one question; content becomes immutable."""
    a = get_assessment(db, college_id, assessment_id)
    _require_draft(a)
    count = question_stats(db, college_id, [a.id]).get(a.id, (0, Decimal("0")))[0]
    if count < 1:
        raise UnprocessableError("Assessment needs at least one question to publish")
    a.status = AssessmentStatus.PUBLISHED
    audit_service.record(
        db, "ASSESSMENT_PUBLISH", "assessment",
        user_id=actor_id, college_id=college_id, resource_id=a.id,
    )
    db.commit()
    return a


def archive(db: Session, college_id: int, actor_id: int, assessment_id: int) -> Assessment:
    """Archive a PUBLISHED assessment."""
    a = get_assessment(db, college_id, assessment_id)
    if a.status != AssessmentStatus.PUBLISHED:
        raise ConflictError("Only PUBLISHED assessments can be archived")
    a.status = AssessmentStatus.ARCHIVED
    audit_service.record(
        db, "ASSESSMENT_ARCHIVE", "assessment",
        user_id=actor_id, college_id=college_id, resource_id=a.id,
    )
    db.commit()
    return a


def new_version(db: Session, college_id: int, actor_id: int, assessment_id: int) -> Assessment:
    """Clone a PUBLISHED/ARCHIVED assessment and its questions into a new DRAFT version."""
    src = get_assessment(db, college_id, assessment_id)
    if src.status == AssessmentStatus.DRAFT:
        raise ConflictError("Only PUBLISHED or ARCHIVED assessments can be versioned")
    latest = db.execute(
        select(func.max(Assessment.version)).where(
            Assessment.college_id == college_id, Assessment.series_key == src.series_key
        )
    ).scalar_one()
    new = Assessment(
        college_id=college_id,
        series_key=src.series_key,
        version=int(latest) + 1,
        title=src.title,
        type=src.type,
        department_id=src.department_id,
        time_limit_min=src.time_limit_min,
        max_attempts=src.max_attempts,
        negative_marking=src.negative_marking,
        status=AssessmentStatus.DRAFT,
        created_by=actor_id,
    )
    db.add(new)
    db.flush()
    for q in db.execute(
        select(AssessmentQuestion).where(
            AssessmentQuestion.assessment_id == src.id,
            AssessmentQuestion.college_id == college_id,
        )
    ).scalars():
        db.add(
            AssessmentQuestion(
                assessment_id=new.id,
                college_id=college_id,
                skill_id=q.skill_id,
                difficulty=q.difficulty,
                body=q.body,
                options=list(q.options),
                correct_option_ids=list(q.correct_option_ids),
                marks=q.marks,
                position=q.position,
            )
        )
    audit_service.record(
        db, "ASSESSMENT_NEW_VERSION", "assessment",
        user_id=actor_id, college_id=college_id, resource_id=new.id,
        metadata={"source_id": src.id, "version": new.version},
    )
    db.commit()
    return new


# ---- questions ------------------------------------------------------------------------------
def validate_question_content(options: list[Option], correct: list[str]) -> None:
    """>=2 options with unique non-empty ids; correct ids non-empty subset of option ids."""
    if len(options) < 2:
        raise UnprocessableError("At least 2 options are required")
    ids = [o.id.strip() for o in options]
    if any(not i for i in ids):
        raise UnprocessableError("Option ids must be non-empty")
    if len(set(ids)) != len(ids):
        raise UnprocessableError("Option ids must be unique")
    if not correct:
        raise UnprocessableError("correct_option_ids must not be empty")
    if not set(correct) <= set(ids):
        raise UnprocessableError("correct_option_ids must be a subset of option ids")


def _check_skill(db: Session, college_id: int, skill_id: int) -> None:
    found = db.execute(
        select(Skill.id).where(Skill.id == skill_id, Skill.college_id == college_id)
    ).first()
    if found is None:
        raise UnprocessableError("Skill not found")


def add_question(
    db: Session, college_id: int, actor_id: int, assessment_id: int, data: QuestionCreate
) -> AdminQuestion:
    """Add a question to a DRAFT assessment."""
    a = get_assessment(db, college_id, assessment_id)
    _require_draft(a)
    validate_question_content(data.options, data.correct_option_ids)
    _check_skill(db, college_id, data.skill_id)
    position = data.position
    if position is None:
        top = db.execute(
            select(func.max(AssessmentQuestion.position)).where(
                AssessmentQuestion.assessment_id == a.id
            )
        ).scalar_one()
        position = 0 if top is None else int(top) + 1
    q = AssessmentQuestion(
        assessment_id=a.id,
        college_id=college_id,
        skill_id=data.skill_id,
        difficulty=data.difficulty,
        body=data.body,
        options=[o.model_dump() for o in data.options],
        correct_option_ids=list(dict.fromkeys(data.correct_option_ids)),
        marks=data.marks,
        position=position,
    )
    db.add(q)
    db.flush()
    audit_service.record(
        db, "QUESTION_CREATE", "assessment_question",
        user_id=actor_id, college_id=college_id, resource_id=q.id,
        metadata={"assessment_id": a.id},
    )
    db.commit()
    return _questions(db, college_id, question_id=q.id)[0]


def _get_question_with_draft_parent(
    db: Session, college_id: int, question_id: int
) -> AssessmentQuestion:
    q = db.execute(
        select(AssessmentQuestion).where(
            AssessmentQuestion.id == question_id, AssessmentQuestion.college_id == college_id
        )
    ).scalar_one_or_none()
    if q is None:
        raise NotFoundError("Question not found")
    _require_draft(get_assessment(db, college_id, q.assessment_id))
    return q


def update_question(
    db: Session, college_id: int, actor_id: int, question_id: int, data: QuestionUpdate
) -> AdminQuestion:
    """Update a question whose assessment is DRAFT."""
    q = _get_question_with_draft_parent(db, college_id, question_id)
    options = data.options if data.options is not None else [Option(**o) for o in q.options]
    correct = (
        data.correct_option_ids
        if data.correct_option_ids is not None
        else [str(c) for c in q.correct_option_ids]
    )
    validate_question_content(options, correct)
    if data.skill_id is not None:
        _check_skill(db, college_id, data.skill_id)
        q.skill_id = data.skill_id
    if data.difficulty is not None:
        q.difficulty = data.difficulty
    if data.body is not None:
        q.body = data.body
    if data.marks is not None:
        q.marks = data.marks
    if data.position is not None:
        q.position = data.position
    q.options = [o.model_dump() for o in options]
    q.correct_option_ids = list(dict.fromkeys(correct))
    audit_service.record(
        db, "QUESTION_UPDATE", "assessment_question",
        user_id=actor_id, college_id=college_id, resource_id=q.id,
    )
    db.commit()
    return _questions(db, college_id, question_id=q.id)[0]


def delete_question(db: Session, college_id: int, actor_id: int, question_id: int) -> None:
    """Delete a question whose assessment is DRAFT."""
    q = _get_question_with_draft_parent(db, college_id, question_id)
    db.delete(q)
    audit_service.record(
        db, "QUESTION_DELETE", "assessment_question",
        user_id=actor_id, college_id=college_id, resource_id=question_id,
    )
    db.commit()
