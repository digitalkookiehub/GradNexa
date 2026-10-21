"""Admin management of companies, tenant scoped."""
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.models import Company, JobDescription, User
from app.schemas.job_admin import CompanyCreate, CompanyOut, CompanyUpdate
from app.services import audit_service

COMPANY_CREATE = "COMPANY_CREATE"
COMPANY_UPDATE = "COMPANY_UPDATE"
COMPANY_DELETE = "COMPANY_DELETE"
DUPLICATE = "A company with this name already exists"


def get_company(db: Session, college_id: int, company_id: int) -> Company:
    """Fetch a company of the college or raise NotFoundError."""
    obj = db.execute(
        select(Company).where(Company.id == company_id, Company.college_id == college_id)
    ).scalar_one_or_none()
    if obj is None:
        raise NotFoundError("Company not found")
    return obj


def _job_counts(db: Session, college_id: int) -> dict[int, int]:
    rows = db.execute(
        select(JobDescription.company_id, func.count(JobDescription.id))
        .where(JobDescription.college_id == college_id)
        .group_by(JobDescription.company_id)
    ).all()
    return {int(c): int(n) for c, n in rows}


def _out(obj: Company, count: int) -> CompanyOut:
    return CompanyOut(
        id=obj.id, name=obj.name, description=obj.description, website=obj.website,
        is_active=obj.is_active, job_count=count,
    )


def to_out(db: Session, obj: Company) -> CompanyOut:
    """Representation of one company."""
    return _out(obj, _job_counts(db, obj.college_id).get(obj.id, 0))


def _name_taken(db: Session, college_id: int, name: str, exclude_id: int | None) -> bool:
    stmt = select(Company.id).where(
        Company.college_id == college_id, func.lower(Company.name) == name.lower()
    )
    if exclude_id is not None:
        stmt = stmt.where(Company.id != exclude_id)
    return db.execute(stmt).first() is not None


def list_companies(db: Session, college_id: int) -> list[CompanyOut]:
    """All companies of the college."""
    counts = _job_counts(db, college_id)
    rows = db.execute(
        select(Company).where(Company.college_id == college_id).order_by(Company.name)
    ).scalars()
    return [_out(c, counts.get(c.id, 0)) for c in rows]


def create_company(db: Session, user: User, payload: CompanyCreate) -> Company:
    """Create a company; duplicate name in the college -> 409."""
    if _name_taken(db, user.college_id, payload.name, None):
        raise ConflictError(DUPLICATE)
    obj = Company(
        college_id=user.college_id, name=payload.name,
        description=payload.description, website=payload.website, is_active=True,
    )
    db.add(obj)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(DUPLICATE) from None
    audit_service.record(
        db, COMPANY_CREATE, "company", user_id=user.id, college_id=user.college_id,
        resource_id=obj.id, metadata={"name": obj.name},
    )
    db.commit()
    return obj


def update_company(db: Session, user: User, company_id: int, payload: CompanyUpdate) -> Company:
    """Apply the provided fields."""
    obj = get_company(db, user.college_id, company_id)
    data = payload.model_dump(exclude_unset=True)
    name = data.get("name")
    if name is not None and _name_taken(db, user.college_id, name, obj.id):
        raise ConflictError(DUPLICATE)
    for key, value in data.items():
        if key in ("name", "is_active") and value is None:
            continue
        setattr(obj, key, value)
    audit_service.record(
        db, COMPANY_UPDATE, "company", user_id=user.id, college_id=user.college_id,
        resource_id=obj.id, metadata={"fields": sorted(data)},
    )
    db.commit()
    return obj


def delete_company(db: Session, user: User, company_id: int) -> None:
    """Delete a company that has no job postings."""
    obj = get_company(db, user.college_id, company_id)
    if _job_counts(db, user.college_id).get(obj.id, 0) > 0:
        raise ConflictError("Company has job postings; deactivate it instead")
    audit_service.record(
        db, COMPANY_DELETE, "company", user_id=user.id, college_id=user.college_id,
        resource_id=obj.id, metadata={"name": obj.name},
    )
    db.delete(obj)
    db.commit()
