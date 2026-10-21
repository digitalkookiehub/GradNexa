"""MCP tool handlers (read-only, tenant scoped). Each handler gets (db, principal, args)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, UnprocessableError
from app.mcp import schemas as s
from app.models import (
    AcademicRecord,
    Assessment,
    AssessmentAttempt,
    AssessmentResult,
    AttemptStatus,
    CareerRole,
    Department,
    LearningPlan,
    ReadinessScore,
    Skill,
    SkillCategory,
    SkillGap,
    Student,
    StudentSkill,
    User,
    UserRole,
)
from app.models.company import Company
from app.models.job_description import JobDescription, JobStatus
from app.schemas.job_student import CompanyOut
from app.services import job_student_service, learning_plan_service, student_service

MAX_GAPS = 10


# ---- shared resolution ----------------------------------------------------------------------
def resolve_student(db: Session, user: User, student_id: int | None) -> Student:
    """The student a call is about. Identity never comes from free text.

    STUDENT: own row (omitted or equal id), created lazily on first use exactly like every other
    student endpoint (``student_service.get_or_create_me``), so a brand-new student who has not
    opened their profile yet still gets an answer instead of a 404. Staff: explicit id checked
    with ``student_service.get_accessible_student`` (faculty assigned only, TPO/ADMIN same college).
    """
    if student_id is None:
        if user.role != UserRole.STUDENT:
            raise UnprocessableError("student_id is required")
        return student_service.get_or_create_me(db, user)
    return student_service.get_accessible_student(db, user, student_id)


def _is_student(user: User) -> bool:
    return user.role == UserRole.STUDENT


def _open_job(db: Session, user: User, job_id: int) -> JobDescription:
    stmt = select(JobDescription).where(
        JobDescription.id == job_id, JobDescription.college_id == user.college_id
    )
    if _is_student(user):
        stmt = stmt.where(JobDescription.status == JobStatus.OPEN)
    job = db.execute(stmt).scalar_one_or_none()
    if job is None:
        raise NotFoundError("Job not found")
    return job


# ---- student tools --------------------------------------------------------------------------
def get_student_profile(db: Session, user: User, args: s.StudentIn) -> s.ProfileOut:
    """Profile of a student (no email or phone)."""
    student = resolve_student(db, user, args.student_id)
    resp = student_service.to_response(db, student)
    name = db.execute(
        select(User.full_name).where(User.id == student.user_id, User.college_id == user.college_id)
    ).scalar_one_or_none()
    return s.ProfileOut(
        student_id=student.id,
        full_name=name or "",
        department_id=resp.department_id,
        department_name=resp.department_name,
        roll_number=resp.roll_number,
        graduation_year=resp.graduation_year,
        profile_complete=resp.profile_complete,
    )


def get_student_academic_record(
    db: Session, user: User, args: s.StudentIn
) -> s.AcademicRecordOut:
    """Academic records (semester CGPA, arrears, attendance)."""
    student = resolve_student(db, user, args.student_id)
    rows = db.execute(
        select(
            AcademicRecord.semester,
            AcademicRecord.cgpa,
            AcademicRecord.active_arrears,
            AcademicRecord.attendance_pct,
        )
        .where(
            AcademicRecord.student_id == student.id,
            AcademicRecord.college_id == student.college_id,
        )
        .order_by(AcademicRecord.semester)
    ).all()
    items = [
        s.AcademicRecordItem(
            semester=int(sem),
            cgpa=float(cgpa),
            active_arrears=int(arr),
            attendance_pct=float(att) if att is not None else None,
        )
        for sem, cgpa, arr, att in rows
    ]
    last = items[-1] if items else None
    return s.AcademicRecordOut(
        student_id=student.id,
        records=items,
        latest_semester=last.semester if last else None,
        latest_cgpa=last.cgpa if last else None,
        latest_attendance_pct=last.attendance_pct if last else None,
    )


def get_student_assessment_results(
    db: Session, user: User, args: s.AssessmentResultsIn
) -> s.AssessmentResultsOut:
    """Submitted assessment results, newest first."""
    student = resolve_student(db, user, args.student_id)
    rows = db.execute(
        select(
            AssessmentAttempt.id,
            Assessment.title,
            AssessmentResult.percentage,
            AssessmentResult.total_score,
            AssessmentResult.max_score,
            AssessmentAttempt.submitted_at,
        )
        .join(Assessment, Assessment.id == AssessmentAttempt.assessment_id)
        .join(AssessmentResult, AssessmentResult.attempt_id == AssessmentAttempt.id)
        .where(
            AssessmentAttempt.student_id == student.id,
            AssessmentAttempt.college_id == student.college_id,
            AssessmentAttempt.status == AttemptStatus.SUBMITTED,
            Assessment.college_id == student.college_id,
            AssessmentResult.college_id == student.college_id,
        )
        .order_by(AssessmentAttempt.submitted_at.desc(), AssessmentAttempt.id.desc())
        .limit(args.limit)
    ).all()
    return s.AssessmentResultsOut(
        student_id=student.id,
        results=[
            s.AssessmentResultItem(
                attempt_id=aid,
                assessment_title=title,
                percentage=float(pct),
                total_score=float(total),
                max_score=float(mx),
                submitted_at=sub,
            )
            for aid, title, pct, total, mx, sub in rows
        ],
    )


def get_student_skill_scores(db: Session, user: User, args: s.StudentIn) -> s.SkillScoresOut:
    """Stored skill scores."""
    student = resolve_student(db, user, args.student_id)
    rows = db.execute(
        select(
            StudentSkill.skill_id,
            Skill.name,
            SkillCategory.name,
            StudentSkill.score,
            StudentSkill.evidence_count,
        )
        .join(Skill, Skill.id == StudentSkill.skill_id)
        .join(SkillCategory, SkillCategory.id == Skill.category_id)
        .where(
            StudentSkill.student_id == student.id,
            StudentSkill.college_id == student.college_id,
            Skill.college_id == student.college_id,
            SkillCategory.college_id == student.college_id,
        )
        .order_by(Skill.name, Skill.id)
    ).all()
    return s.SkillScoresOut(
        student_id=student.id,
        skills=[
            s.SkillScoreItem(
                skill_id=sid, skill_name=sn, category_name=cn, score=float(sc), evidence_count=ev
            )
            for sid, sn, cn, sc, ev in rows
        ],
    )


_PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNASSESSED": 3, "NONE": 4}


def _gap_items(db: Session, score: ReadinessScore) -> list[s.GapItem]:
    rows = db.execute(
        select(SkillGap, Skill.name)
        .join(Skill, Skill.id == SkillGap.skill_id)
        .where(
            SkillGap.readiness_score_id == score.id,
            SkillGap.college_id == score.college_id,
            Skill.college_id == score.college_id,
        )
    ).all()
    items = [
        s.GapItem(
            skill_id=g.skill_id,
            skill_name=name,
            current=float(g.current) if g.current is not None else None,
            required=float(g.required),
            gap=float(g.gap) if g.gap is not None else None,
            status=g.status.value,
            priority=g.priority.value,
            recommended_action=g.recommended_action,
        )
        for g, name in rows
    ]
    items.sort(key=lambda i: (_PRIORITY_ORDER.get(i.priority, 9), -(i.gap or 0.0), i.skill_id))
    return items[:MAX_GAPS]


def _readiness_summary(
    db: Session, student: Student, role_id: int | None
) -> s.ReadinessSummary | None:
    stmt = select(ReadinessScore).where(
        ReadinessScore.student_id == student.id, ReadinessScore.college_id == student.college_id
    )
    if role_id is not None:
        stmt = stmt.where(ReadinessScore.role_id == role_id)
    score = db.execute(
        stmt.order_by(ReadinessScore.computed_at.desc(), ReadinessScore.id.desc()).limit(1)
    ).scalar_one_or_none()
    if score is None:
        return None
    role_name: str | None = None
    if score.role_id is not None:
        role_name = db.execute(
            select(CareerRole.name).where(
                CareerRole.id == score.role_id, CareerRole.college_id == score.college_id
            )
        ).scalar_one_or_none()
    return s.ReadinessSummary(
        role_id=score.role_id,
        role_name=role_name,
        overall=float(score.overall) if score.overall is not None else None,
        level=score.level,
        coverage=float(score.coverage),
        rule_version=score.rule_version,
        computed_at=score.computed_at,
        gaps=_gap_items(db, score) if score.role_id is not None else [],
    )


def _plan_progress(
    plan: LearningPlan, role_name: str, done: int, total: int, percent: float
) -> s.PlanProgress:
    return s.PlanProgress(
        plan_id=plan.id,
        role_id=plan.role_id,
        role_name=role_name,
        status=plan.status.value,
        starts_on=plan.starts_on,
        done=done,
        total=total,
        percent=percent,
    )


def get_student_progress(db: Session, user: User, args: s.ProgressIn) -> s.ProgressOut:
    """Active plan progress and the latest STORED readiness summary (never recomputed)."""
    student = resolve_student(db, user, args.student_id)
    plan_out: s.PlanProgress | None = None
    plan = learning_plan_service._active_plan(db, student)
    if plan is not None:
        prog = learning_plan_service._progress_for(db, plan.college_id, [plan.id])[plan.id]
        role_name = db.execute(
            select(CareerRole.name).where(
                CareerRole.id == plan.role_id, CareerRole.college_id == plan.college_id
            )
        ).scalar_one_or_none()
        plan_out = _plan_progress(plan, role_name or "", prog.done, prog.total, prog.percent)
    return s.ProgressOut(
        student_id=student.id,
        plan=plan_out,
        latest_readiness=_readiness_summary(db, student, args.role_id),
    )


# ---- college-wide tools ---------------------------------------------------------------------
def get_department_details(db: Session, user: User, args: s.DepartmentIn) -> s.DepartmentOut:
    """A department of the caller's college and its active career roles."""
    dept_id = args.department_id
    if dept_id is None:
        if not _is_student(user):
            raise UnprocessableError("department_id is required")
        dept_id = db.execute(
            select(Student.department_id).where(
                Student.user_id == user.id, Student.college_id == user.college_id
            )
        ).scalar_one_or_none()
        if dept_id is None:
            raise NotFoundError("Department not found")
    dept = db.execute(
        select(Department).where(
            Department.id == dept_id, Department.college_id == user.college_id
        )
    ).scalar_one_or_none()
    if dept is None:
        raise NotFoundError("Department not found")
    roles = db.execute(
        select(CareerRole.id, CareerRole.name)
        .where(
            CareerRole.college_id == user.college_id,
            CareerRole.department_id == dept.id,
            CareerRole.is_active.is_(True),
        )
        .order_by(CareerRole.name, CareerRole.id)
    ).all()
    return s.DepartmentOut(
        department_id=dept.id,
        name=dept.name,
        code=dept.code,
        is_active=dept.is_active,
        career_roles=[s.RoleRef(id=i, name=n) for i, n in roles],
    )


def get_eligibility_rules(
    db: Session, user: User, args: s.JobEligibilityIn
) -> s.EligibilityRulesOut:
    """Configured criteria of a job; evaluation only when a student is resolvable."""
    job = _open_job(db, user, args.job_id)
    rule = job_student_service._rules_for(db, job.college_id, [job.id]).get(job.id)
    evaluation = None
    if args.student_id is not None or _is_student(user):
        student = resolve_student(db, user, args.student_id)
        if job.status == JobStatus.OPEN:
            evaluation = job_student_service.get_eligibility(db, user, student, job.id)
    return s.EligibilityRulesOut(
        job_id=job.id,
        job_title=job.title,
        has_rule=rule is not None,
        criteria=job_student_service._criteria_out(db, rule) if rule is not None else None,
        evaluation=evaluation,
    )


def _job_skills(db: Session, job: JobDescription) -> list[s.JobSkillOut]:
    reqs = sorted(
        job_student_service.job_requirements(db, job), key=lambda r: (r.skill_name, r.skill_id)
    )
    return [
        s.JobSkillOut(
            skill_id=r.skill_id,
            skill_name=r.skill_name,
            required_level=r.required_level,
            weight=r.weight,
        )
        for r in reqs
    ]


def _company_out(company: Company) -> CompanyOut:
    return CompanyOut(
        id=company.id,
        name=company.name,
        description=company.description,
        website=company.website,
    )


def get_company_requirements(
    db: Session, user: User, args: s.CompanyIn
) -> s.CompanyRequirementsOut:
    """Company and the required skills of its OPEN jobs."""
    stmt = select(Company).where(
        Company.id == args.company_id, Company.college_id == user.college_id
    )
    if _is_student(user):
        stmt = stmt.where(Company.is_active.is_(True))
    company = db.execute(stmt).scalar_one_or_none()
    if company is None:
        raise NotFoundError("Company not found")
    jobs = list(
        db.execute(
            select(JobDescription)
            .where(
                JobDescription.company_id == company.id,
                JobDescription.college_id == user.college_id,
                JobDescription.status == JobStatus.OPEN,
            )
            .order_by(JobDescription.id)
        ).scalars()
    )
    return s.CompanyRequirementsOut(
        company=_company_out(company),
        open_jobs=[
            s.CompanyJob(
                job_id=j.id,
                title=j.title,
                role_id=j.role_id,
                application_deadline=j.application_deadline,
                skills=_job_skills(db, j),
            )
            for j in jobs
        ],
    )


def get_job_description(db: Session, user: User, args: s.JobIn) -> s.JobDescriptionOut:
    """Job description with skills and criteria (OPEN jobs only for students)."""
    job = _open_job(db, user, args.job_id)
    company = db.execute(
        select(Company).where(Company.id == job.company_id, Company.college_id == job.college_id)
    ).scalar_one()
    rule = job_student_service._rules_for(db, job.college_id, [job.id]).get(job.id)
    return s.JobDescriptionOut(
        id=job.id,
        company=_company_out(company),
        title=job.title,
        body=job.body,
        role_id=job.role_id,
        role_name=job_student_service._role_name(db, job),
        status=job.status.value,
        application_deadline=job.application_deadline,
        deadline_passed=job_student_service._deadline_passed(job.application_deadline),
        skills=_job_skills(db, job),
        eligibility_criteria=(
            job_student_service._criteria_out(db, rule) if rule is not None else None
        ),
    )
