"""ADMIN endpoints: readiness rule versions and career roles."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import CareerRole, User, UserRole
from app.schemas.readiness import (
    CareerRoleCreate,
    CareerRoleDetailResponse,
    CareerRoleResponse,
    CareerRoleUpdate,
    ReadinessRuleCreate,
    ReadinessRuleResponse,
    RoleSkillIn,
)
from app.services import career_role_service, readiness_rule_service

router = APIRouter(prefix="/admin", tags=["admin-readiness"])
AdminUser = Depends(require_role(UserRole.ADMIN))


@router.get("/readiness-rules", response_model=list[ReadinessRuleResponse])
async def list_rules(
    admin: User = AdminUser, db: Session = Depends(get_db)
) -> list[ReadinessRuleResponse]:
    """All readiness rule versions of the admin's college."""
    return [
        readiness_rule_service.to_response(r)
        for r in readiness_rule_service.list_rules(db, admin.college_id)
    ]


@router.get("/readiness-rules/{rule_id}", response_model=ReadinessRuleResponse)
async def get_rule(
    rule_id: int, admin: User = AdminUser, db: Session = Depends(get_db)
) -> ReadinessRuleResponse:
    """One readiness rule version."""
    return readiness_rule_service.to_response(
        readiness_rule_service.get_rule(db, admin.college_id, rule_id)
    )


@router.post("/readiness-rules", response_model=ReadinessRuleResponse, status_code=201)
async def create_rule(
    payload: ReadinessRuleCreate, admin: User = AdminUser, db: Session = Depends(get_db)
) -> ReadinessRuleResponse:
    """Create the next (inactive) rule version."""
    rule = readiness_rule_service.create_rule(db, admin.college_id, admin.id, payload)
    return readiness_rule_service.to_response(rule)


@router.post("/readiness-rules/{rule_id}/activate", response_model=ReadinessRuleResponse)
async def activate_rule(
    rule_id: int, admin: User = AdminUser, db: Session = Depends(get_db)
) -> ReadinessRuleResponse:
    """Activate a rule version; the previously active one is deactivated."""
    rule = readiness_rule_service.activate_rule(db, admin.college_id, admin.id, rule_id)
    return readiness_rule_service.to_response(rule)


@router.get("/career-roles", response_model=list[CareerRoleResponse])
async def list_roles(admin: User = AdminUser, db: Session = Depends(get_db)) -> list[CareerRole]:
    """All career roles of the college including inactive ones."""
    return career_role_service.list_roles(db, admin.college_id)


@router.post("/career-roles", response_model=CareerRoleResponse, status_code=201)
async def create_role(
    payload: CareerRoleCreate, admin: User = AdminUser, db: Session = Depends(get_db)
) -> CareerRole:
    """Create a career role."""
    return career_role_service.create_role(db, admin.college_id, admin.id, payload)


@router.get("/career-roles/{role_id}", response_model=CareerRoleDetailResponse)
async def get_role(
    role_id: int, admin: User = AdminUser, db: Session = Depends(get_db)
) -> CareerRoleDetailResponse:
    """A career role with its skill requirements."""
    return career_role_service.to_detail(
        db, career_role_service.get_role(db, admin.college_id, role_id)
    )


@router.put("/career-roles/{role_id}", response_model=CareerRoleResponse)
async def update_role(
    role_id: int,
    payload: CareerRoleUpdate,
    admin: User = AdminUser,
    db: Session = Depends(get_db),
) -> CareerRole:
    """Update a career role."""
    return career_role_service.update_role(db, admin.college_id, admin.id, role_id, payload)


@router.put("/career-roles/{role_id}/skills", response_model=CareerRoleDetailResponse)
async def replace_role_skills(
    role_id: int,
    payload: list[RoleSkillIn],
    admin: User = AdminUser,
    db: Session = Depends(get_db),
) -> CareerRoleDetailResponse:
    """Bulk-replace the skill requirements of a role."""
    role = career_role_service.replace_skills(db, admin.college_id, admin.id, role_id, payload)
    return career_role_service.to_detail(db, role)
