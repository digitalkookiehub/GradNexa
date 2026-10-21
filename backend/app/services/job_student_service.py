"""Student-facing job reads, deterministic eligibility and job skill-fit (tenant scoped).

Eligibility (``eligibility_engine``) and skill-fit (``readiness_engine``) are computed
separately and never combined. Nothing here is persisted except audit rows.
"""
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.models import AcademicRecord, CareerRole, Department, Skill, SkillCategory, Student, User
from app.models.company import Company
from app.models.eligibility_rule import EligibilityRule
from app.models.job_description import JobDescription, JobStatus
from app.models.job_skill import JobSkill
from app.schemas.job_student import (
    CompanyOut,
    CriterionOut,
    DepartmentRef,
    EligibilityResponse,
    EligibilityRuleOut,
    JobDetail,
    JobListItem,
    JobSkillOut,
    SkillFitResponse,
)
from app.schemas.readiness import GapResponse
from app.services import audit_service, eligibility_engine, readiness_engine
from app.services import readiness_rule_service as rule_svc
from app.services.eligibility_engine import RecordFact, RuleInput, StudentFacts
from app.services.readiness_engine import RoleRequirement
from app.services.readiness_service import _load_evidence, _rule_config

ELIGIBILITY_READ = "JOB_ELIGIBILITY_READ"
SKILL_FIT_READ = "JOB_SKILL_FIT_READ"


def _today() -> date:
    return datetime.now(UTC).date()


def _deadline_passed(deadline: date | None) -> bool:
    return deadline is not None and deadline < _today()


def get_open_job(db: Session, student: Student, job_id: int) -> JobDescription:
    """An OPEN job of the student's college, else NotFoundError."""
    job = db.execute(
        select(JobDescription).where(
            JobDescription.id == job_id,
            JobDescription.college_id == student.college_id,
            JobDescription.status == JobStatus.OPEN,
        )
    ).scalar_one_or_none()
    if job is None:
        raise NotFoundError("Job not found")
    return job


def _facts(db: Session, student: Student) -> StudentFacts:
    rows = db.execute(
        select(
            AcademicRecord.semester,
            AcademicRecord.cgpa,
            AcademicRecord.active_arrears,
            AcademicRecord.attendance_pct,
        ).where(
            AcademicRecord.student_id == student.id,
            AcademicRecord.college_id == student.college_id,
        )
    ).all()
    dept_name: str | None = None
    if student.department_id is not None:
        dept_name = db.execute(
            select(Department.name).where(
                Department.id == student.department_id,
                Department.college_id == student.college_id,
            )
        ).scalar_one_or_none()
    return StudentFacts(
        department_id=student.department_id,
        graduation_year=student.graduation_year,
        records=[RecordFact(int(s), Decimal(c), int(a), p) for s, c, a, p in rows],
        department_name=dept_name,
    )


def _rule_input(rule: EligibilityRule, dept_names: dict[int, str]) -> RuleInput:
    return RuleInput(
        cgpa_min=rule.cgpa_min,
        cgpa_basis=rule.cgpa_basis.value if rule.cgpa_basis is not None else None,
        max_arrears=rule.max_arrears,
        attendance_min=rule.attendance_min,
        department_ids=rule.department_ids,
        graduation_years=rule.graduation_years,
        custom_notes=list(rule.custom_notes or []),
        department_names=dept_names,
    )


def _department_names(db: Session, college_id: int, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = db.execute(
        select(Department.id, Department.name).where(
            Department.college_id == college_id, Department.id.in_(ids)
        )
    ).all()
    return {int(i): str(n) for i, n in rows}


def _rules_for(db: Session, college_id: int, job_ids: Sequence[int]) -> dict[int, EligibilityRule]:
    if not job_ids:
        return {}
    rules = db.execute(
        select(EligibilityRule).where(
            EligibilityRule.college_id == college_id, EligibilityRule.job_id.in_(job_ids)
        )
    ).scalars()
    return {r.job_id: r for r in rules}


def list_jobs(db: Session, student: Student) -> list[JobListItem]:
    """Open jobs with the caller's eligibility status (bulk loaded, no per-job queries)."""
    rows = db.execute(
        select(JobDescription, Company.name, CareerRole.name)
        .join(Company, Company.id == JobDescription.company_id)
        .outerjoin(
            CareerRole,
            (CareerRole.id == JobDescription.role_id)
            & (CareerRole.college_id == JobDescription.college_id),
        )
        .where(
            JobDescription.college_id == student.college_id,
            JobDescription.status == JobStatus.OPEN,
            Company.college_id == student.college_id,
        )
        .order_by(
            JobDescription.application_deadline.is_(None),
            JobDescription.application_deadline,
            JobDescription.id,
        )
    ).all()
    rules = _rules_for(db, student.college_id, [j.id for j, _, _ in rows])
    facts = _facts(db, student)
    items: list[JobListItem] = []
    for job, company_name, role_name in rows:
        rule = rules.get(job.id)
        result = eligibility_engine.evaluate(
            _rule_input(rule, {}) if rule is not None else None, facts
        )
        items.append(
            JobListItem(
                id=job.id,
                company_id=job.company_id,
                company_name=company_name,
                title=job.title,
                role_id=job.role_id,
                role_name=role_name,
                status=job.status.value,
                application_deadline=job.application_deadline,
                deadline_passed=_deadline_passed(job.application_deadline),
                has_eligibility_rule=rule is not None,
                eligibility_status=result.status,  # type: ignore[arg-type]
            )
        )
    return items


def _role_name(db: Session, job: JobDescription) -> str | None:
    if job.role_id is None:
        return None
    return db.execute(
        select(CareerRole.name).where(
            CareerRole.id == job.role_id, CareerRole.college_id == job.college_id
        )
    ).scalar_one_or_none()


def job_requirements(db: Session, job: JobDescription) -> list[RoleRequirement]:
    """Job skills as engine requirements."""
    rows = db.execute(
        select(JobSkill, Skill.name, SkillCategory.id, SkillCategory.name)
        .join(Skill, Skill.id == JobSkill.skill_id)
        .join(SkillCategory, SkillCategory.id == Skill.category_id)
        .where(
            JobSkill.job_id == job.id,
            JobSkill.college_id == job.college_id,
            Skill.college_id == job.college_id,
            SkillCategory.college_id == job.college_id,
        )
    ).all()
    return [
        RoleRequirement(
            skill_id=js.skill_id,
            skill_name=sname,
            category_id=cid,
            category_name=cname,
            required_level=float(js.required_level),
            weight=float(js.weight),
        )
        for js, sname, cid, cname in rows
    ]


def _criteria_out(db: Session, rule: EligibilityRule) -> EligibilityRuleOut:
    names = _department_names(db, rule.college_id, set(rule.department_ids or []))
    return EligibilityRuleOut(
        cgpa_min=float(rule.cgpa_min) if rule.cgpa_min is not None else None,
        cgpa_basis=rule.cgpa_basis.value if rule.cgpa_basis is not None else None,
        max_arrears=rule.max_arrears,
        attendance_min=float(rule.attendance_min) if rule.attendance_min is not None else None,
        department_ids=(
            [DepartmentRef(id=i, name=names.get(i, f"Department {i}")) for i in rule.department_ids]
            if rule.department_ids is not None
            else None
        ),
        graduation_years=(
            list(rule.graduation_years) if rule.graduation_years is not None else None
        ),
        custom_notes=[str(n) for n in (rule.custom_notes or [])],
    )


def get_detail(db: Session, student: Student, job_id: int) -> JobDetail:
    """Job detail with skills and configured eligibility criteria."""
    job = get_open_job(db, student, job_id)
    company = db.execute(
        select(Company).where(Company.id == job.company_id, Company.college_id == job.college_id)
    ).scalar_one()
    skills = sorted(job_requirements(db, job), key=lambda r: (r.skill_name, r.skill_id))
    rule = _rules_for(db, job.college_id, [job.id]).get(job.id)
    return JobDetail(
        id=job.id,
        company=CompanyOut(
            id=company.id, name=company.name, description=company.description,
            website=company.website,
        ),
        title=job.title,
        body=job.body,
        role_id=job.role_id,
        role_name=_role_name(db, job),
        status=job.status.value,
        application_deadline=job.application_deadline,
        deadline_passed=_deadline_passed(job.application_deadline),
        skills=[
            JobSkillOut(
                skill_id=r.skill_id, skill_name=r.skill_name,
                required_level=r.required_level, weight=r.weight,
            )
            for r in skills
        ],
        eligibility_criteria=_criteria_out(db, rule) if rule is not None else None,
    )


def get_eligibility(db: Session, user: User, student: Student, job_id: int) -> EligibilityResponse:
    """Evaluate the job's configured criteria for the caller (audited)."""
    job = get_open_job(db, student, job_id)
    rule = _rules_for(db, job.college_id, [job.id]).get(job.id)
    rule_in: RuleInput | None = None
    if rule is not None:
        names = _department_names(db, job.college_id, set(rule.department_ids or []))
        rule_in = _rule_input(rule, names)
    result = eligibility_engine.evaluate(rule_in, _facts(db, student))
    audit_service.record(
        db, ELIGIBILITY_READ, "job", user_id=user.id, college_id=user.college_id,
        resource_id=job.id, metadata={"status": result.status},
    )
    db.commit()
    return EligibilityResponse(
        job_id=job.id,
        status=result.status,  # type: ignore[arg-type]
        criteria=[
            CriterionOut(
                key=c.key, label=c.label, required=c.required, actual=c.actual,
                result=c.result,  # type: ignore[arg-type]
            )
            for c in result.criteria
        ],
        custom_notes=result.custom_notes,
        evaluated_at=datetime.now(UTC),
    )


def get_skill_fit(db: Session, user: User, student: Student, job_id: int) -> SkillFitResponse:
    """Gaps against the job's skills using the active readiness rule (not persisted)."""
    job = get_open_job(db, student, job_id)
    rule = rule_svc.get_active_rule(db, student.college_id)
    if rule is None:
        raise ConflictError("No active readiness rule configured")
    result = readiness_engine.compute_role(
        _rule_config(rule), job_requirements(db, job), _load_evidence(db, student)
    )
    audit_service.record(
        db, SKILL_FIT_READ, "job", user_id=user.id, college_id=user.college_id,
        resource_id=job.id, metadata={"rule_id": rule.id, "rule_version": rule.version},
    )
    db.commit()
    return SkillFitResponse(
        job_id=job.id,
        rule_id=rule.id,
        rule_version=rule.version,
        overall=result.overall,
        coverage=result.coverage,
        gaps=[
            GapResponse(
                skill_id=g.skill_id, skill_name=g.skill_name, current=g.current,
                required=g.required, gap=g.gap,
                status=g.status,  # type: ignore[arg-type]
                priority=g.priority,  # type: ignore[arg-type]
                recommended_action=g.recommended_action,
            )
            for g in result.gaps
        ],
    )
