"""Career role and role-skill logic (tenant scoped)."""
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models import CareerRole, Department, RoleSkill, Skill, Student
from app.schemas.readiness import (
    CareerRoleCreate,
    CareerRoleDetailResponse,
    CareerRoleUpdate,
    RoleSkillIn,
    RoleSkillResponse,
)
from app.services import audit_service


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


def _name_taken(db: Session, college_id: int, name: str, exclude_id: int | None) -> bool:
    stmt = select(CareerRole.id).where(CareerRole.college_id == college_id, CareerRole.name == name)
    if exclude_id is not None:
        stmt = stmt.where(CareerRole.id != exclude_id)
    return db.execute(stmt).first() is not None


def get_role(db: Session, college_id: int, role_id: int) -> CareerRole:
    """Fetch a role of the college (active or not) or raise NotFoundError."""
    role = db.execute(
        select(CareerRole).where(CareerRole.id == role_id, CareerRole.college_id == college_id)
    ).scalar_one_or_none()
    if role is None:
        raise NotFoundError("Career role not found")
    return role


def list_roles(db: Session, college_id: int) -> list[CareerRole]:
    """All roles of the college including inactive ones (admin view)."""
    stmt = select(CareerRole).where(CareerRole.college_id == college_id).order_by(CareerRole.name)
    return list(db.execute(stmt).scalars())


def _visible(role: CareerRole, student: Student) -> bool:
    return role.is_active and (
        role.department_id is None or role.department_id == student.department_id
    )


def list_visible_roles(db: Session, student: Student) -> list[CareerRole]:
    """Active roles visible to the student (no department, or the student's department)."""
    return [r for r in list_roles(db, student.college_id) if _visible(r, student)]


def get_visible_role(db: Session, student: Student, role_id: int) -> CareerRole:
    """An active role of the student's college visible to them, else NotFoundError."""
    role = get_role(db, student.college_id, role_id)
    if not _visible(role, student):
        raise NotFoundError("Career role not found")
    return role


def list_role_skills(db: Session, college_id: int, role_id: int) -> list[RoleSkillResponse]:
    """Skill requirements of a role."""
    stmt = (
        select(RoleSkill, Skill.name)
        .join(Skill, Skill.id == RoleSkill.skill_id)
        .where(
            RoleSkill.role_id == role_id,
            RoleSkill.college_id == college_id,
            Skill.college_id == college_id,
        )
        .order_by(Skill.name, Skill.id)
    )
    return [
        RoleSkillResponse(
            skill_id=rs.skill_id,
            skill_name=name,
            required_level=float(rs.required_level),
            weight=float(rs.weight),
        )
        for rs, name in db.execute(stmt).all()
    ]


def to_detail(db: Session, role: CareerRole) -> CareerRoleDetailResponse:
    """Role with its skills."""
    return CareerRoleDetailResponse(
        id=role.id,
        department_id=role.department_id,
        name=role.name,
        description=role.description,
        is_active=role.is_active,
        skills=list_role_skills(db, role.college_id, role.id),
    )


def create_role(db: Session, college_id: int, actor_id: int, data: CareerRoleCreate) -> CareerRole:
    """Create a role."""
    name = data.name.strip()
    _check_department(db, college_id, data.department_id)
    if _name_taken(db, college_id, name, None):
        raise ConflictError("Career role name already exists")
    role = CareerRole(
        college_id=college_id,
        department_id=data.department_id,
        name=name,
        description=data.description,
        is_active=data.is_active,
    )
    db.add(role)
    db.flush()
    audit_service.record(
        db,
        "CAREER_ROLE_CREATE",
        "career_role",
        user_id=actor_id,
        college_id=college_id,
        resource_id=role.id,
    )
    db.commit()
    return role


def update_role(
    db: Session, college_id: int, actor_id: int, role_id: int, data: CareerRoleUpdate
) -> CareerRole:
    """Update a role (only fields present in the payload)."""
    role = get_role(db, college_id, role_id)
    fields = data.model_dump(exclude_unset=True)
    if fields.get("name") is not None:
        name = str(fields["name"]).strip()
        if _name_taken(db, college_id, name, role.id):
            raise ConflictError("Career role name already exists")
        role.name = name
    if "department_id" in fields:
        _check_department(db, college_id, fields["department_id"])
        role.department_id = fields["department_id"]
    if "description" in fields:
        role.description = fields["description"]
    if fields.get("is_active") is not None:
        role.is_active = bool(fields["is_active"])
    audit_service.record(
        db,
        "CAREER_ROLE_UPDATE",
        "career_role",
        user_id=actor_id,
        college_id=college_id,
        resource_id=role.id,
        metadata={"fields": sorted(fields)},
    )
    db.commit()
    return role


def replace_skills(
    db: Session, college_id: int, actor_id: int, role_id: int, items: list[RoleSkillIn]
) -> CareerRole:
    """Bulk-replace the role's skill requirements."""
    role = get_role(db, college_id, role_id)
    ids = [i.skill_id for i in items]
    if len(set(ids)) != len(ids):
        raise UnprocessableError("Duplicate skill_id in payload")
    if ids:
        found = set(
            db.execute(
                select(Skill.id).where(Skill.college_id == college_id, Skill.id.in_(ids))
            ).scalars()
        )
        if found != set(ids):
            raise UnprocessableError("Unknown skill in payload")
    db.execute(
        delete(RoleSkill).where(RoleSkill.role_id == role.id, RoleSkill.college_id == college_id)
    )
    for item in items:
        db.add(
            RoleSkill(
                role_id=role.id,
                college_id=college_id,
                skill_id=item.skill_id,
                required_level=item.required_level,
                weight=item.weight,
            )
        )
    audit_service.record(
        db,
        "CAREER_ROLE_SKILLS_UPDATE",
        "career_role",
        user_id=actor_id,
        college_id=college_id,
        resource_id=role.id,
        metadata={"skill_count": len(items)},
    )
    db.commit()
    return role
