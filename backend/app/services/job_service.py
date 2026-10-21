"""Admin management of job descriptions, job skills and eligibility rules, tenant scoped."""
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models import (
    CareerRole,
    Company,
    Department,
    EligibilityRule,
    JobDescription,
    JobSkill,
    JobStatus,
    Skill,
    User,
)
from app.schemas.job_admin import (
    DepartmentRef,
    EligibilityIn,
    EligibilityRuleOut,
    JobCreate,
    JobOut,
    JobSkillIn,
    JobSkillOut,
    JobSummary,
    JobUpdate,
)
from app.services import audit_service, company_service

JOB_CREATE = "JOB_CREATE"
JOB_UPDATE = "JOB_UPDATE"
JOB_DELETE = "JOB_DELETE"
JOB_PUBLISH = "JOB_PUBLISH"
JOB_CLOSE = "JOB_CLOSE"
JOB_SKILLS_REPLACE = "JOB_SKILLS_REPLACE"
JOB_ELIGIBILITY_SET = "JOB_ELIGIBILITY_SET"
JOB_ELIGIBILITY_DELETE = "JOB_ELIGIBILITY_DELETE"


def _f(value: object) -> float | None:
    return None if value is None else float(value)  # type: ignore[arg-type]


def _d(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def get_job(db: Session, college_id: int, job_id: int) -> JobDescription:
    """Fetch a job of the college or raise NotFoundError."""
    obj = db.execute(
        select(JobDescription).where(
            JobDescription.id == job_id, JobDescription.college_id == college_id
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NotFoundError("Job not found")
    return obj


def _check_role(db: Session, college_id: int, role_id: int | None) -> None:
    if role_id is None:
        return
    found = db.execute(
        select(CareerRole.id).where(CareerRole.id == role_id, CareerRole.college_id == college_id)
    ).first()
    if found is None:
        raise UnprocessableError("Unknown role")


def _role_names(db: Session, college_id: int) -> dict[int, str]:
    rows = db.execute(
        select(CareerRole.id, CareerRole.name).where(CareerRole.college_id == college_id)
    ).all()
    return {int(i): str(n) for i, n in rows}


def _company_names(db: Session, college_id: int) -> dict[int, str]:
    rows = db.execute(
        select(Company.id, Company.name).where(Company.college_id == college_id)
    ).all()
    return {int(i): str(n) for i, n in rows}


def _rule_job_ids(db: Session, college_id: int) -> set[int]:
    rows = db.execute(
        select(EligibilityRule.job_id).where(EligibilityRule.college_id == college_id)
    ).all()
    return {int(r[0]) for r in rows}


def _summary(
    job: JobDescription, companies: dict[int, str], roles: dict[int, str], with_rule: set[int]
) -> JobSummary:
    return JobSummary(
        id=job.id, company_id=job.company_id, company_name=companies.get(job.company_id, ""),
        title=job.title, role_id=job.role_id,
        role_name=roles.get(job.role_id) if job.role_id is not None else None,
        status=job.status, application_deadline=job.application_deadline,
        has_eligibility_rule=job.id in with_rule,
    )


def list_jobs(
    db: Session, college_id: int, company_id: int | None, status: JobStatus | None
) -> list[JobSummary]:
    """Jobs of the college, optionally filtered."""
    stmt = select(JobDescription).where(JobDescription.college_id == college_id)
    if company_id is not None:
        stmt = stmt.where(JobDescription.company_id == company_id)
    if status is not None:
        stmt = stmt.where(JobDescription.status == status)
    companies = _company_names(db, college_id)
    roles = _role_names(db, college_id)
    with_rule = _rule_job_ids(db, college_id)
    rows = db.execute(stmt.order_by(JobDescription.id.desc())).scalars()
    return [_summary(j, companies, roles, with_rule) for j in rows]


def _skills_out(db: Session, job: JobDescription) -> list[JobSkillOut]:
    rows = db.execute(
        select(JobSkill, Skill.name)
        .join(Skill, Skill.id == JobSkill.skill_id)
        .where(JobSkill.job_id == job.id, JobSkill.college_id == job.college_id)
        .order_by(Skill.name)
    ).all()
    return [
        JobSkillOut(
            skill_id=js.skill_id, skill_name=str(name),
            required_level=float(js.required_level), weight=float(js.weight),
        )
        for js, name in rows
    ]


def _rule(db: Session, job: JobDescription) -> EligibilityRule | None:
    return db.execute(
        select(EligibilityRule).where(
            EligibilityRule.job_id == job.id, EligibilityRule.college_id == job.college_id
        )
    ).scalar_one_or_none()


def _rule_out(db: Session, rule: EligibilityRule) -> EligibilityRuleOut:
    depts: list[DepartmentRef] | None = None
    if rule.department_ids is not None:
        ids = [int(i) for i in rule.department_ids]
        rows = db.execute(
            select(Department.id, Department.name).where(
                Department.college_id == rule.college_id, Department.id.in_(ids)
            )
        ).all()
        names = {int(i): str(n) for i, n in rows}
        depts = [DepartmentRef(id=i, name=names[i]) for i in ids if i in names]
    years = (
        [int(y) for y in rule.graduation_years] if rule.graduation_years is not None else None
    )
    return EligibilityRuleOut(
        cgpa_min=_f(rule.cgpa_min), cgpa_basis=rule.cgpa_basis, max_arrears=rule.max_arrears,
        attendance_min=_f(rule.attendance_min), department_ids=depts,
        graduation_years=years,
        custom_notes=[str(n) for n in (rule.custom_notes or [])],
    )


def to_out(db: Session, job: JobDescription) -> JobOut:
    """Full job representation."""
    cid = job.college_id
    rule = _rule(db, job)
    base = _summary(
        job, _company_names(db, cid), _role_names(db, cid), {job.id} if rule is not None else set()
    )
    return JobOut(
        **base.model_dump(), body=job.body, created_by=job.created_by,
        skills=_skills_out(db, job),
        eligibility=_rule_out(db, rule) if rule is not None else None,
    )


def _audit(db: Session, user: User, action: str, job_id: int, meta: dict[str, object]) -> None:
    audit_service.record(
        db, action, "job", user_id=user.id, college_id=user.college_id,
        resource_id=job_id, metadata=meta,
    )


def create_job(db: Session, user: User, payload: JobCreate) -> JobDescription:
    """Create a DRAFT job for an active company of the college."""
    company = company_service.get_company(db, user.college_id, payload.company_id)
    if not company.is_active:
        raise UnprocessableError("Company is not active")
    _check_role(db, user.college_id, payload.role_id)
    job = JobDescription(
        college_id=user.college_id, company_id=company.id, role_id=payload.role_id,
        title=payload.title, body=payload.body, status=JobStatus.DRAFT,
        application_deadline=payload.application_deadline, created_by=user.id,
    )
    db.add(job)
    db.flush()
    _audit(db, user, JOB_CREATE, job.id, {"title": job.title, "company_id": company.id})
    db.commit()
    return job


def _require_not_closed(job: JobDescription) -> None:
    if job.status == JobStatus.CLOSED:
        raise ConflictError("Job is closed and cannot be modified")


def update_job(db: Session, user: User, job_id: int, payload: JobUpdate) -> JobDescription:
    """Apply provided fields; explicit null clears role_id / application_deadline."""
    job = get_job(db, user.college_id, job_id)
    _require_not_closed(job)
    data = payload.model_dump(exclude_unset=True)
    if data.get("role_id") is not None:
        _check_role(db, user.college_id, data["role_id"])
    for key, value in data.items():
        setattr(job, key, value)
    _audit(db, user, JOB_UPDATE, job.id, {"fields": sorted(data)})
    db.commit()
    return job


def delete_job(db: Session, user: User, job_id: int) -> None:
    """Delete a DRAFT job with its skills and eligibility rule."""
    job = get_job(db, user.college_id, job_id)
    if job.status != JobStatus.DRAFT:
        raise ConflictError("Close the job instead")
    db.execute(
        delete(JobSkill).where(JobSkill.job_id == job.id, JobSkill.college_id == job.college_id)
    )
    db.execute(
        delete(EligibilityRule).where(
            EligibilityRule.job_id == job.id, EligibilityRule.college_id == job.college_id
        )
    )
    _audit(db, user, JOB_DELETE, job.id, {"title": job.title})
    db.delete(job)
    db.commit()


def publish_job(db: Session, user: User, job_id: int) -> JobDescription:
    """DRAFT -> OPEN."""
    job = get_job(db, user.college_id, job_id)
    if job.status != JobStatus.DRAFT:
        raise ConflictError("Only a draft job can be published")
    job.status = JobStatus.OPEN
    _audit(db, user, JOB_PUBLISH, job.id, {})
    db.commit()
    return job


def close_job(db: Session, user: User, job_id: int) -> JobDescription:
    """OPEN -> CLOSED."""
    job = get_job(db, user.college_id, job_id)
    if job.status != JobStatus.OPEN:
        raise ConflictError("Only an open job can be closed")
    job.status = JobStatus.CLOSED
    _audit(db, user, JOB_CLOSE, job.id, {})
    db.commit()
    return job


def replace_skills(
    db: Session, user: User, job_id: int, items: list[JobSkillIn]
) -> list[JobSkillOut]:
    """Bulk replace the job's skills."""
    job = get_job(db, user.college_id, job_id)
    _require_not_closed(job)
    ids = [i.skill_id for i in items]
    if len(set(ids)) != len(ids):
        raise UnprocessableError("Duplicate skill_id")
    if ids:
        found = {
            int(r[0])
            for r in db.execute(
                select(Skill.id).where(Skill.college_id == user.college_id, Skill.id.in_(ids))
            ).all()
        }
        if found != set(ids):
            raise UnprocessableError("Unknown skill")
    db.execute(
        delete(JobSkill).where(JobSkill.job_id == job.id, JobSkill.college_id == job.college_id)
    )
    for item in items:
        db.add(JobSkill(
            job_id=job.id, college_id=job.college_id, skill_id=item.skill_id,
            required_level=item.required_level, weight=item.weight,
        ))
    db.flush()
    _audit(db, user, JOB_SKILLS_REPLACE, job.id, {"skill_ids": sorted(ids)})
    db.commit()
    return _skills_out(db, job)


def set_eligibility(
    db: Session, user: User, job_id: int, payload: EligibilityIn
) -> EligibilityRuleOut:
    """Upsert the job's eligibility rule (omitted fields mean no criterion)."""
    job = get_job(db, user.college_id, job_id)
    if payload.department_ids is not None:
        found = {
            int(r[0])
            for r in db.execute(
                select(Department.id).where(
                    Department.college_id == user.college_id,
                    Department.id.in_(payload.department_ids),
                )
            ).all()
        }
        if found != set(payload.department_ids):
            raise UnprocessableError("Unknown department")
    rule = _rule(db, job)
    if rule is None:
        rule = EligibilityRule(job_id=job.id, college_id=job.college_id)
        db.add(rule)
    rule.cgpa_min = _d(payload.cgpa_min)
    rule.cgpa_basis = payload.cgpa_basis
    rule.max_arrears = payload.max_arrears
    rule.attendance_min = _d(payload.attendance_min)
    rule.department_ids = payload.department_ids
    rule.graduation_years = payload.graduation_years
    rule.custom_notes = payload.custom_notes or []
    db.flush()
    _audit(db, user, JOB_ELIGIBILITY_SET, job.id, {"fields": sorted(payload.model_fields_set)})
    db.commit()
    return _rule_out(db, rule)


def delete_eligibility(db: Session, user: User, job_id: int) -> None:
    """Remove the job's eligibility rule (404 if none)."""
    job = get_job(db, user.college_id, job_id)
    rule = _rule(db, job)
    if rule is None:
        raise NotFoundError("Eligibility rule not found")
    db.delete(rule)
    _audit(db, user, JOB_ELIGIBILITY_DELETE, job.id, {})
    db.commit()
