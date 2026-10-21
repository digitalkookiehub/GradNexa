"""Student career goals and the student-facing role additions (tenant scoped)."""
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.exceptions import UnprocessableError
from app.models import CareerRole, ReadinessScore, Student, StudentCareerGoal, User
from app.schemas.planning import (
    GoalIn,
    GoalResponse,
    MyReadiness,
    StudentCareerRoleDetailResponse,
    StudentCareerRoleResponse,
)
from app.schemas.readiness import CareerRoleDetailResponse
from app.services import audit_service, career_role_service

GOALS_UPDATE = "CAREER_GOALS_UPDATE"


def list_goals(db: Session, student: Student) -> list[GoalResponse]:
    """The student's goals ordered by priority."""
    stmt = (
        select(StudentCareerGoal.career_role_id, CareerRole.name, StudentCareerGoal.priority)
        .join(CareerRole, CareerRole.id == StudentCareerGoal.career_role_id)
        .where(
            StudentCareerGoal.student_id == student.id,
            StudentCareerGoal.college_id == student.college_id,
            CareerRole.college_id == student.college_id,
        )
        .order_by(StudentCareerGoal.priority, StudentCareerGoal.id)
    )
    return [
        GoalResponse(career_role_id=rid, role_name=name, priority=prio)
        for rid, name, prio in db.execute(stmt).all()
    ]


def replace_goals(
    db: Session, user: User, student: Student, items: list[GoalIn]
) -> list[GoalResponse]:
    """Bulk replace the goals. Duplicates are 422; non-visible roles are 404."""
    role_ids = [i.career_role_id for i in items]
    if len(set(role_ids)) != len(role_ids):
        raise UnprocessableError("Duplicate career_role_id in payload")
    priorities = [i.priority for i in items]
    if len(set(priorities)) != len(priorities):
        raise UnprocessableError("Duplicate priority in payload")
    for role_id in role_ids:
        career_role_service.get_visible_role(db, student, role_id)
    db.execute(
        delete(StudentCareerGoal).where(
            StudentCareerGoal.student_id == student.id,
            StudentCareerGoal.college_id == student.college_id,
        )
    )
    for item in items:
        db.add(
            StudentCareerGoal(
                student_id=student.id,
                college_id=student.college_id,
                career_role_id=item.career_role_id,
                priority=item.priority,
            )
        )
    audit_service.record(
        db,
        GOALS_UPDATE,
        "student_career_goal",
        user_id=user.id,
        college_id=user.college_id,
        resource_id=student.id,
        metadata={"role_ids": role_ids},
    )
    db.commit()
    return list_goals(db, student)


def goal_role_ids(db: Session, student: Student) -> set[int]:
    """Role ids the student has as goals."""
    return set(
        db.execute(
            select(StudentCareerGoal.career_role_id).where(
                StudentCareerGoal.student_id == student.id,
                StudentCareerGoal.college_id == student.college_id,
            )
        ).scalars()
    )


def list_roles_for_student(db: Session, student: Student) -> list[StudentCareerRoleResponse]:
    """Visible roles with the ``is_goal`` flag."""
    goals = goal_role_ids(db, student)
    return [
        StudentCareerRoleResponse.model_validate(r, from_attributes=True).model_copy(
            update={"is_goal": r.id in goals}
        )
        for r in career_role_service.list_visible_roles(db, student)
    ]


def my_readiness(db: Session, student: Student, role_id: int) -> MyReadiness | None:
    """Latest stored role-specific readiness of the student, or None."""
    score = db.execute(
        select(ReadinessScore)
        .where(
            ReadinessScore.student_id == student.id,
            ReadinessScore.college_id == student.college_id,
            ReadinessScore.role_id == role_id,
        )
        .order_by(ReadinessScore.computed_at.desc(), ReadinessScore.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if score is None:
        return None
    return MyReadiness(
        overall=float(score.overall) if score.overall is not None else None,
        level=score.level,
        coverage=float(score.coverage),
        rule_version=score.rule_version,
        computed_at=score.computed_at,
    )


def role_detail_for_student(
    db: Session, student: Student, role: CareerRole
) -> StudentCareerRoleDetailResponse:
    """Role detail plus ``is_goal`` and ``my_readiness``."""
    detail: CareerRoleDetailResponse = career_role_service.to_detail(db, role)
    return StudentCareerRoleDetailResponse(
        **detail.model_dump(),
        is_goal=role.id in goal_role_ids(db, student),
        my_readiness=my_readiness(db, student, role.id),
    )
