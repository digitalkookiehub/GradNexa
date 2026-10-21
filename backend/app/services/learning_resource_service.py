"""Learning resource curation (staff) and approved-resource listing (students), tenant scoped."""
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, UnprocessableError
from app.models import LearningPlanItem, LearningResource, Skill, User
from app.schemas.planning import ResourceAdmin, ResourceCreate, ResourcePublic, ResourceUpdate
from app.services import audit_service

RESOURCE_CREATE = "LEARNING_RESOURCE_CREATE"
RESOURCE_UPDATE = "LEARNING_RESOURCE_UPDATE"
RESOURCE_DELETE = "LEARNING_RESOURCE_DELETE"
RESOURCE_APPROVE = "LEARNING_RESOURCE_APPROVE"
RESOURCE_UNAPPROVE = "LEARNING_RESOURCE_UNAPPROVE"


def _check_skill(db: Session, college_id: int, skill_id: int) -> None:
    found = db.execute(
        select(Skill.id).where(Skill.id == skill_id, Skill.college_id == college_id)
    ).first()
    if found is None:
        raise UnprocessableError("Unknown skill")


def get_resource(db: Session, college_id: int, resource_id: int) -> LearningResource:
    """Fetch a resource of the college or raise NotFoundError."""
    res = db.execute(
        select(LearningResource).where(
            LearningResource.id == resource_id, LearningResource.college_id == college_id
        )
    ).scalar_one_or_none()
    if res is None:
        raise NotFoundError("Learning resource not found")
    return res


def _skill_names(db: Session, college_id: int) -> dict[int, str]:
    rows = db.execute(select(Skill.id, Skill.name).where(Skill.college_id == college_id)).all()
    return {int(i): str(n) for i, n in rows}


def _admin(res: LearningResource, names: dict[int, str]) -> ResourceAdmin:
    return ResourceAdmin(
        id=res.id,
        skill_id=res.skill_id,
        skill_name=names.get(res.skill_id, ""),
        title=res.title,
        url=res.url,
        description=res.description,
        is_approved=res.is_approved,
        approved_by=res.approved_by,
        approved_at=res.approved_at,
        created_by=res.created_by,
    )


def to_admin(db: Session, res: LearningResource) -> ResourceAdmin:
    """Staff representation of one resource."""
    return _admin(res, _skill_names(db, res.college_id))


def list_admin(
    db: Session, college_id: int, skill_id: int | None, approved: bool | None
) -> list[ResourceAdmin]:
    """All resources of the college, optionally filtered."""
    stmt = select(LearningResource).where(LearningResource.college_id == college_id)
    if skill_id is not None:
        stmt = stmt.where(LearningResource.skill_id == skill_id)
    if approved is not None:
        stmt = stmt.where(LearningResource.is_approved.is_(approved))
    names = _skill_names(db, college_id)
    rows = db.execute(stmt.order_by(LearningResource.id)).scalars()
    return [_admin(r, names) for r in rows]


def list_approved(db: Session, college_id: int, skill_id: int | None) -> list[ResourcePublic]:
    """Approved resources of the college (the only ones students may see)."""
    stmt = (
        select(LearningResource, Skill.name)
        .join(Skill, Skill.id == LearningResource.skill_id)
        .where(
            LearningResource.college_id == college_id,
            LearningResource.is_approved.is_(True),
            Skill.college_id == college_id,
        )
        .order_by(Skill.name, LearningResource.id)
    )
    if skill_id is not None:
        stmt = stmt.where(LearningResource.skill_id == skill_id)
    return [
        ResourcePublic(
            id=r.id,
            skill_id=r.skill_id,
            skill_name=name,
            title=r.title,
            url=r.url,
            description=r.description,
        )
        for r, name in db.execute(stmt).all()
    ]


def create_resource(db: Session, actor: User, data: ResourceCreate) -> LearningResource:
    """Create an unapproved resource."""
    _check_skill(db, actor.college_id, data.skill_id)
    res = LearningResource(
        college_id=actor.college_id,
        skill_id=data.skill_id,
        title=data.title.strip(),
        url=data.url,
        description=data.description,
        is_approved=False,
        created_by=actor.id,
    )
    db.add(res)
    db.flush()
    audit_service.record(
        db,
        RESOURCE_CREATE,
        "learning_resource",
        user_id=actor.id,
        college_id=actor.college_id,
        resource_id=res.id,
        metadata={"skill_id": res.skill_id},
    )
    db.commit()
    return res


def _reset_approval(res: LearningResource) -> None:
    res.is_approved = False
    res.approved_by = None
    res.approved_at = None


def update_resource(
    db: Session, actor: User, resource_id: int, data: ResourceUpdate
) -> LearningResource:
    """Update a resource; changing url or skill resets approval."""
    res = get_resource(db, actor.college_id, resource_id)
    fields = data.model_dump(exclude_unset=True)
    reset = False
    if fields.get("title") is not None:
        res.title = str(fields["title"]).strip()
    if "description" in fields:
        res.description = fields["description"]
    if fields.get("url") is not None and fields["url"] != res.url:
        res.url = str(fields["url"])
        reset = True
    if fields.get("skill_id") is not None and fields["skill_id"] != res.skill_id:
        _check_skill(db, actor.college_id, int(fields["skill_id"]))
        res.skill_id = int(fields["skill_id"])
        reset = True
    if reset:
        _reset_approval(res)
    audit_service.record(
        db,
        RESOURCE_UPDATE,
        "learning_resource",
        user_id=actor.id,
        college_id=actor.college_id,
        resource_id=res.id,
        metadata={"fields": sorted(fields), "approval_reset": reset},
    )
    db.commit()
    return res


def delete_resource(db: Session, actor: User, resource_id: int) -> None:
    """Delete a resource (plan items referencing it keep their text, resource set to null)."""
    res = get_resource(db, actor.college_id, resource_id)
    # Detach plan items explicitly so they keep their text without the resource.
    for item in db.execute(
        select(LearningPlanItem).where(
            LearningPlanItem.resource_id == res.id,
            LearningPlanItem.college_id == actor.college_id,
        )
    ).scalars():
        item.resource_id = None
    db.flush()
    db.execute(
        delete(LearningResource).where(
            LearningResource.id == res.id, LearningResource.college_id == actor.college_id
        )
    )
    audit_service.record(
        db,
        RESOURCE_DELETE,
        "learning_resource",
        user_id=actor.id,
        college_id=actor.college_id,
        resource_id=resource_id,
    )
    db.commit()


def set_approval(db: Session, actor: User, resource_id: int, approve: bool) -> LearningResource:
    """Approve or unapprove a resource (ADMIN only; enforced by the router)."""
    res = get_resource(db, actor.college_id, resource_id)
    if approve:
        res.is_approved = True
        res.approved_by = actor.id
        res.approved_at = datetime.now(UTC)
    else:
        _reset_approval(res)
    audit_service.record(
        db,
        RESOURCE_APPROVE if approve else RESOURCE_UNAPPROVE,
        "learning_resource",
        user_id=actor.id,
        college_id=actor.college_id,
        resource_id=res.id,
    )
    db.commit()
    return res
