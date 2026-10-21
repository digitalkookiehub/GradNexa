"""Skill category and skill logic (tenant scoped)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models import Department, Skill, SkillCategory, SkillScope, StudentSkill
from app.schemas.assessment import (
    SkillCategoryCreate,
    SkillCategoryUpdate,
    SkillCreate,
    SkillResponse,
    SkillUpdate,
    StudentSkillResponse,
)
from app.services import audit_service


def list_categories(db: Session, college_id: int) -> list[SkillCategory]:
    """All skill categories of the college."""
    stmt = (
        select(SkillCategory)
        .where(SkillCategory.college_id == college_id)
        .order_by(SkillCategory.name)
    )
    return list(db.execute(stmt).scalars())


def _check_scope(
    db: Session, college_id: int, scope: SkillScope, department_id: int | None
) -> None:
    if scope == SkillScope.DEPARTMENT and department_id is None:
        raise UnprocessableError("department_id is required for DEPARTMENT scope")
    if scope == SkillScope.COMMON and department_id is not None:
        raise UnprocessableError("department_id must be empty for COMMON scope")
    if department_id is not None:
        found = db.execute(
            select(Department.id).where(
                Department.id == department_id, Department.college_id == college_id
            )
        ).first()
        if found is None:
            raise UnprocessableError("Department not found")


def _category_name_taken(db: Session, college_id: int, name: str, exclude_id: int | None) -> bool:
    stmt = select(SkillCategory.id).where(
        SkillCategory.college_id == college_id, SkillCategory.name == name
    )
    if exclude_id is not None:
        stmt = stmt.where(SkillCategory.id != exclude_id)
    return db.execute(stmt).first() is not None


def get_category(db: Session, college_id: int, category_id: int) -> SkillCategory:
    """Fetch a category of the college or raise NotFoundError."""
    cat = db.execute(
        select(SkillCategory).where(
            SkillCategory.id == category_id, SkillCategory.college_id == college_id
        )
    ).scalar_one_or_none()
    if cat is None:
        raise NotFoundError("Skill category not found")
    return cat


def create_category(
    db: Session, college_id: int, actor_id: int, data: SkillCategoryCreate
) -> SkillCategory:
    """Create a category."""
    name = data.name.strip()
    _check_scope(db, college_id, data.scope, data.department_id)
    if _category_name_taken(db, college_id, name, None):
        raise ConflictError("Skill category name already exists")
    cat = SkillCategory(
        college_id=college_id, name=name, scope=data.scope, department_id=data.department_id
    )
    db.add(cat)
    db.flush()
    audit_service.record(
        db, "SKILL_CATEGORY_CREATE", "skill_category",
        user_id=actor_id, college_id=college_id, resource_id=cat.id,
    )
    db.commit()
    return cat


def update_category(
    db: Session, college_id: int, actor_id: int, category_id: int, data: SkillCategoryUpdate
) -> SkillCategory:
    """Update a category."""
    cat = get_category(db, college_id, category_id)
    fields = data.model_fields_set
    name = data.name.strip() if data.name is not None else cat.name
    scope = data.scope if data.scope is not None else cat.scope
    dept = data.department_id if "department_id" in fields else cat.department_id
    if scope == SkillScope.COMMON and "department_id" not in fields:
        dept = None
    _check_scope(db, college_id, scope, dept)
    if _category_name_taken(db, college_id, name, cat.id):
        raise ConflictError("Skill category name already exists")
    cat.name, cat.scope, cat.department_id = name, scope, dept
    audit_service.record(
        db, "SKILL_CATEGORY_UPDATE", "skill_category",
        user_id=actor_id, college_id=college_id, resource_id=cat.id,
    )
    db.commit()
    return cat


def list_skills(db: Session, college_id: int) -> list[SkillResponse]:
    """All skills of the college with category names."""
    stmt = (
        select(Skill, SkillCategory.name)
        .join(SkillCategory, SkillCategory.id == Skill.category_id)
        .where(Skill.college_id == college_id, SkillCategory.college_id == college_id)
        .order_by(SkillCategory.name, Skill.name)
    )
    return [to_skill_response(s, cname) for s, cname in db.execute(stmt).all()]


def to_skill_response(skill: Skill, category_name: str) -> SkillResponse:
    """Build a SkillResponse."""
    return SkillResponse(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        category_id=skill.category_id,
        category_name=category_name,
    )


def get_skill(db: Session, college_id: int, skill_id: int) -> Skill:
    """Fetch a skill of the college or raise NotFoundError."""
    skill = db.execute(
        select(Skill).where(Skill.id == skill_id, Skill.college_id == college_id)
    ).scalar_one_or_none()
    if skill is None:
        raise NotFoundError("Skill not found")
    return skill


def _skill_name_taken(db: Session, college_id: int, name: str, exclude_id: int | None) -> bool:
    stmt = select(Skill.id).where(Skill.college_id == college_id, Skill.name == name)
    if exclude_id is not None:
        stmt = stmt.where(Skill.id != exclude_id)
    return db.execute(stmt).first() is not None


def create_skill(db: Session, college_id: int, actor_id: int, data: SkillCreate) -> SkillResponse:
    """Create a skill in an existing category of the college."""
    try:
        cat = get_category(db, college_id, data.category_id)
    except NotFoundError as exc:
        raise UnprocessableError("Skill category not found") from exc
    name = data.name.strip()
    if _skill_name_taken(db, college_id, name, None):
        raise ConflictError("Skill name already exists")
    skill = Skill(
        college_id=college_id, category_id=cat.id, name=name, description=data.description
    )
    db.add(skill)
    db.flush()
    audit_service.record(
        db, "SKILL_CREATE", "skill", user_id=actor_id, college_id=college_id, resource_id=skill.id
    )
    db.commit()
    return to_skill_response(skill, cat.name)


def update_skill(
    db: Session, college_id: int, actor_id: int, skill_id: int, data: SkillUpdate
) -> SkillResponse:
    """Update a skill."""
    skill = get_skill(db, college_id, skill_id)
    if data.category_id is not None:
        try:
            skill.category_id = get_category(db, college_id, data.category_id).id
        except NotFoundError as exc:
            raise UnprocessableError("Skill category not found") from exc
    if data.name is not None:
        name = data.name.strip()
        if _skill_name_taken(db, college_id, name, skill.id):
            raise ConflictError("Skill name already exists")
        skill.name = name
    if "description" in data.model_fields_set:
        skill.description = data.description
    audit_service.record(
        db, "SKILL_UPDATE", "skill", user_id=actor_id, college_id=college_id, resource_id=skill.id
    )
    db.commit()
    cat = get_category(db, college_id, skill.category_id)
    return to_skill_response(skill, cat.name)


def list_student_skills(
    db: Session, college_id: int, student_id: int
) -> list[StudentSkillResponse]:
    """The student's skill scores."""
    stmt = (
        select(StudentSkill, Skill.name, SkillCategory.name)
        .join(Skill, Skill.id == StudentSkill.skill_id)
        .join(SkillCategory, SkillCategory.id == Skill.category_id)
        .where(
            StudentSkill.student_id == student_id,
            StudentSkill.college_id == college_id,
            Skill.college_id == college_id,
        )
        .order_by(SkillCategory.name, Skill.name)
    )
    return [
        StudentSkillResponse(
            skill_id=ss.skill_id,
            skill_name=sname,
            category_name=cname,
            score=float(ss.score),
            evidence_count=ss.evidence_count,
            confidence=float(ss.confidence) if ss.confidence is not None else None,
            updated_at=ss.updated_at,
        )
        for ss, sname, cname in db.execute(stmt).all()
    ]
