"""Student-facing jobs API: visibility, eligibility, skill-fit, isolation, audit, N+1."""
import json
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.models import (
    AcademicRecord,
    AuditLog,
    CareerRole,
    College,
    Department,
    ReadinessRule,
    Skill,
    SkillCategory,
    Student,
    StudentSkill,
    User,
    UserRole,
)
from app.models.company import Company
from app.models.eligibility_rule import CgpaBasis, EligibilityRule
from app.models.job_description import JobDescription, JobStatus
from app.models.job_skill import JobSkill

API = "/api/v1"
Headers = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


class Env:
    def __init__(
        self, client: TestClient, db: Session, h: Headers, make_user: MakeUser,
        a: College, b: College,
    ) -> None:
        self.client, self.db, self.h, self.a, self.b = client, db, h, a, b
        self.others = {r: make_user(a, r) for r in UserRole if r != UserRole.STUDENT}
        self.admin = self.others[UserRole.ADMIN]
        self.student = make_user(a, UserRole.STUDENT)
        self.student_b = make_user(b, UserRole.STUDENT)
        self.dept = self._add(Department(college_id=a.id, name="Computer Science", code="CS"))
        self.dept2 = self._add(Department(college_id=a.id, name="Electronics", code="EC"))
        self.cat = self._add(SkillCategory(college_id=a.id, name="Tech"))
        self.py = self._add(Skill(college_id=a.id, category_id=self.cat.id, name="Python"))
        self.sql = self._add(Skill(college_id=a.id, category_id=self.cat.id, name="SQL"))
        self.me = self._add(
            Student(user_id=self.student.id, college_id=a.id, department_id=self.dept.id,
                    graduation_year=2026)
        )
        self.company = self._add(Company(college_id=a.id, name="Acme", website="https://acme.io"))
        self.company_b = self._add(Company(college_id=b.id, name="Acme"))
        self.role = self._add(CareerRole(college_id=a.id, name="Backend Dev"))

    def _add(self, obj: Any) -> Any:
        self.db.add(obj)
        self.db.commit()
        return obj

    def req(self, path: str, user: User) -> Any:
        return self.client.get(API + path, headers=self.h(user))

    def job(
        self, title: str = "SDE", status: JobStatus = JobStatus.OPEN, college: College | None = None,
        deadline: date | None = None, body: str = "Build things", role: bool = False,
    ) -> JobDescription:
        c = college or self.a
        company = self.company if c.id == self.a.id else self.company_b
        return self._add(
            JobDescription(
                college_id=c.id, company_id=company.id, title=title, body=body, status=status,
                application_deadline=deadline, created_by=self.admin.id,
                role_id=self.role.id if role else None,
            )
        )

    def rule(self, job: JobDescription, **kw: Any) -> EligibilityRule:
        return self._add(EligibilityRule(job_id=job.id, college_id=job.college_id, **kw))

    def job_skill(self, job: JobDescription, skill: Skill, level: int, weight: int = 1) -> None:
        self._add(
            JobSkill(job_id=job.id, college_id=job.college_id, skill_id=skill.id,
                     required_level=level, weight=weight)
        )

    def record(self, sem: int, cgpa: str, arrears: int = 0, att: str | None = "80") -> None:
        self._add(
            AcademicRecord(student_id=self.me.id, college_id=self.a.id, semester=sem,
                           cgpa=Decimal(cgpa), active_arrears=arrears,
                           attendance_pct=Decimal(att) if att else None)
        )

    def readiness_rule(self, college: College | None = None) -> ReadinessRule:
        c = college or self.a
        return self._add(
            ReadinessRule(
                college_id=c.id, version=1, is_active=True, created_by=self.admin.id,
                weights={str(self.cat.id): 100},
                level_thresholds=[{"level": "Foundation", "min_score": 0}],
                gap_thresholds={"high_min_gap": 30, "medium_min_gap": 15},
            )
        )

    def actions(self) -> list[str]:
        return list(self.db.execute(select(AuditLog.action)).scalars())


@pytest.fixture
def env(
    client: TestClient, db: Session, auth_headers: Headers, make_user: MakeUser,
    college: College, other_college: College,
) -> Env:
    return Env(client, db, auth_headers, make_user, college, other_college)


def test_visibility_open_only_and_cross_college(env: Env) -> None:
    open_job = env.job("Open")
    draft = env.job("Draft", JobStatus.DRAFT)
    closed = env.job("Closed", JobStatus.CLOSED)
    other = env.job("Other", college=env.b)
    ids = [j["id"] for j in env.req("/jobs", env.student).json()]
    assert ids == [open_job.id]
    for hidden in (draft, closed, other):
        for suffix in ("", "/eligibility", "/skill-fit"):
            r = env.req(f"/jobs/{hidden.id}{suffix}", env.student)
            assert r.status_code == 404, (hidden.title, suffix)
            assert r.json() == {"detail": "Job not found"}
    assert env.req("/jobs/99999", env.student).status_code == 404
    # second college's student sees only own college's job
    assert [j["title"] for j in env.req("/jobs", env.student_b).json()] == ["Other"]
    assert env.req(f"/jobs/{open_job.id}", env.student_b).status_code == 404


def test_role_guards(env: Env) -> None:
    job = env.job()
    for role, user in env.others.items():
        for suffix in ("", f"/{job.id}", f"/{job.id}/eligibility", f"/{job.id}/skill-fit"):
            assert env.req(f"/jobs{suffix}", user).status_code == 403, (role, suffix)
    assert env.client.get(f"{API}/jobs").status_code in (401, 403)


def test_list_ordering_and_fields(env: Env) -> None:
    today = datetime.now(UTC).date()
    late = env.job("Late", deadline=today + timedelta(days=10))
    none = env.job("NoDeadline")
    early = env.job("Early", deadline=today + timedelta(days=2), role=True)
    past = env.job("Past", deadline=today - timedelta(days=1))
    rows = env.req("/jobs", env.student).json()
    assert [r["id"] for r in rows] == [past.id, early.id, late.id, none.id]
    by_id = {r["id"]: r for r in rows}
    assert by_id[past.id]["deadline_passed"] is True
    assert by_id[early.id]["deadline_passed"] is False
    assert by_id[early.id]["role_name"] == "Backend Dev"
    assert by_id[late.id]["role_id"] is None and by_id[late.id]["role_name"] is None
    assert by_id[late.id]["company_name"] == "Acme"
    assert set(rows[0]) == {
        "id", "company_id", "company_name", "title", "role_id", "role_name", "status",
        "application_deadline", "deadline_passed", "has_eligibility_rule", "eligibility_status",
    }


def test_list_eligibility_statuses(env: Env) -> None:
    env.record(1, "8.00", 0, "80")
    no_rule = env.job("NoRule")
    empty_rule = env.job("EmptyRule")
    env.rule(empty_rule, custom_notes=["Only note"])
    ok = env.job("Ok")
    env.rule(ok, cgpa_min=Decimal("8.00"), cgpa_basis=CgpaBasis.LATEST_SEMESTER)
    bad = env.job("Bad")
    env.rule(bad, cgpa_min=Decimal("9"), cgpa_basis=CgpaBasis.LATEST_SEMESTER)
    unknown = env.job("Unknown")
    env.rule(unknown, graduation_years=[2026], department_ids=[env.dept.id], max_arrears=0)
    # student has graduation year; remove it to make UNKNOWN
    env.me.graduation_year = None
    env.db.commit()
    rows = {r["title"]: r for r in env.req("/jobs", env.student).json()}
    assert rows["NoRule"]["eligibility_status"] == "NO_RULE"
    assert rows["NoRule"]["has_eligibility_rule"] is False
    assert rows["EmptyRule"]["eligibility_status"] == "NO_RULE"
    assert rows["EmptyRule"]["has_eligibility_rule"] is True
    assert rows["Ok"]["eligibility_status"] == "ELIGIBLE"
    assert rows["Bad"]["eligibility_status"] == "NOT_ELIGIBLE"
    assert rows["Unknown"]["eligibility_status"] == "INCOMPLETE_DATA"
    assert no_rule.id in {r["id"] for r in rows.values()}


def test_detail(env: Env) -> None:
    job = env.job(body="Python and SQL needed", role=True, deadline=datetime.now(UTC).date())
    env.job_skill(job, env.sql, 60, 1)
    env.job_skill(job, env.py, 70, 3)
    env.rule(
        job, cgpa_min=Decimal("7.5"), cgpa_basis=CgpaBasis.AVERAGE_ALL_SEMESTERS,
        max_arrears=1, department_ids=[env.dept.id, env.dept2.id], custom_notes=["Bring ID"],
    )
    d = env.req(f"/jobs/{job.id}", env.student).json()
    assert d["company"] == {
        "id": env.company.id, "name": "Acme", "description": None, "website": "https://acme.io",
    }
    assert d["role_name"] == "Backend Dev" and d["status"] == "OPEN"
    assert d["deadline_passed"] is False  # deadline day itself is still open
    assert [s["skill_name"] for s in d["skills"]] == ["Python", "SQL"]
    assert d["skills"][0]["required_level"] == 70.0 and d["skills"][0]["weight"] == 3.0
    crit = d["eligibility_criteria"]
    assert crit == {
        "cgpa_min": 7.5, "cgpa_basis": "AVERAGE_ALL_SEMESTERS", "max_arrears": 1,
        "attendance_min": None,
        "department_ids": [
            {"id": env.dept.id, "name": "Computer Science"},
            {"id": env.dept2.id, "name": "Electronics"},
        ],
        "graduation_years": None, "custom_notes": ["Bring ID"],
    }
    bare = env.job("Bare")
    assert env.req(f"/jobs/{bare.id}", env.student).json()["eligibility_criteria"] is None


def test_eligibility_endpoint_and_audit(env: Env) -> None:
    env.record(1, "9.00", 0, "70")
    env.record(2, "7.00", 2, "74.5")
    job = env.job()
    env.rule(
        job, cgpa_min=Decimal("8.00"), cgpa_basis=CgpaBasis.AVERAGE_ALL_SEMESTERS,
        max_arrears=1, attendance_min=Decimal("75"), department_ids=[env.dept.id],
        graduation_years=[2026], custom_notes=["Original marksheets"],
    )
    r = env.req(f"/jobs/{job.id}/eligibility", env.student)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["job_id"] == job.id and body["status"] == "NOT_ELIGIBLE"
    assert body["note"] == (
        "Eligibility reflects the configured criteria only. "
        "Custom notes are not evaluated automatically."
    )
    assert body["custom_notes"] == ["Original marksheets"]
    assert body["evaluated_at"]
    crit = {c["key"]: c for c in body["criteria"]}
    assert crit["cgpa"]["actual"] == "8.00" and crit["cgpa"]["result"] == "MET"
    assert crit["arrears"]["actual"] == "2" and crit["arrears"]["result"] == "NOT_MET"
    assert crit["attendance"]["actual"] == "74.50%" and crit["attendance"]["result"] == "NOT_MET"
    assert crit["department"]["actual"] == "Computer Science"
    assert crit["graduation_year"]["result"] == "MET"
    assert set(crit["cgpa"]) == {"key", "label", "required", "actual", "result"}
    assert env.actions().count("JOB_ELIGIBILITY_READ") == 1
    row = env.db.execute(
        select(AuditLog).where(AuditLog.action == "JOB_ELIGIBILITY_READ")
    ).scalar_one()
    assert row.resource_id == str(job.id) and row.user_id == env.student.id
    assert row.college_id == env.a.id


def test_eligibility_no_rule_and_unknown(env: Env) -> None:
    job = env.job()
    b = env.req(f"/jobs/{job.id}/eligibility", env.student).json()
    assert b["status"] == "NO_RULE" and b["criteria"] == []
    env.rule(job, cgpa_min=Decimal("7"), cgpa_basis=CgpaBasis.LATEST_SEMESTER)
    b = env.req(f"/jobs/{job.id}/eligibility", env.student).json()
    assert b["status"] == "INCOMPLETE_DATA"
    assert b["criteria"][0]["actual"] is None and b["criteria"][0]["result"] == "UNKNOWN"


def test_skill_fit(env: Env) -> None:
    job = env.job()
    env.job_skill(job, env.py, 80, 3)
    env.job_skill(job, env.sql, 50, 1)
    r = env.req(f"/jobs/{job.id}/skill-fit", env.student)
    assert r.status_code == 409 and r.json() == {"detail": "No active readiness rule configured"}
    rule = env.readiness_rule()
    env._add(StudentSkill(student_id=env.me.id, college_id=env.a.id, skill_id=env.py.id,
                          score=Decimal("60"), evidence_count=1))
    r = env.req(f"/jobs/{job.id}/skill-fit", env.student)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rule_id"] == rule.id and body["rule_version"] == 1
    assert body["overall"] == 60.0 and body["coverage"] == 75.0
    gaps = {g["skill_name"]: g for g in body["gaps"]}
    assert gaps["Python"]["gap"] == 20.0 and gaps["Python"]["priority"] == "MEDIUM"
    assert gaps["Python"]["status"] == "GAP"
    assert gaps["SQL"]["status"] == "NO_EVIDENCE" and gaps["SQL"]["current"] is None
    assert set(gaps["Python"]) == {
        "skill_id", "skill_name", "current", "required", "gap", "status", "priority",
        "recommended_action",
    }
    # nothing persisted
    from app.models import ReadinessScore, SkillGap
    assert env.db.execute(select(ReadinessScore.id)).first() is None
    assert env.db.execute(select(SkillGap.id)).first() is None
    assert env.actions().count("JOB_SKILL_FIT_READ") == 1


def test_skill_fit_empty_and_other_college_rule_ignored(env: Env) -> None:
    job = env.job()
    env.readiness_rule(env.b)  # only another college has an active rule
    assert env.req(f"/jobs/{job.id}/skill-fit", env.student).status_code == 409
    env.readiness_rule()
    body = env.req(f"/jobs/{job.id}/skill-fit", env.student).json()
    assert body["gaps"] == [] and body["overall"] is None and body["coverage"] == 0.0


def test_eligibility_and_skill_fit_are_separate(env: Env) -> None:
    env.record(1, "8", 0, "80")
    job = env.job()
    env.job_skill(job, env.py, 80)
    env.rule(job, cgpa_min=Decimal("7"), cgpa_basis=CgpaBasis.LATEST_SEMESTER)
    env.readiness_rule()
    elig = json.dumps(env.req(f"/jobs/{job.id}/eligibility", env.student).json()).lower()
    fit = json.dumps(env.req(f"/jobs/{job.id}/skill-fit", env.student).json()).lower()
    for word in ("readiness", "overall", "coverage", "gap", "priority", "skill"):
        assert word not in elig, word
    for word in ("eligib", "cgpa", "arrears", "attendance", "met"):
        assert word not in fit, word
    for word in ("selected", "probability", "chance"):
        assert word not in elig and word not in fit


def test_cross_college_rule_does_not_leak(env: Env) -> None:
    """Rules/skills are always loaded scoped by the job's college."""
    job_b = env.job("B job", college=env.b)
    other_student = env.student_b
    assert env.req(f"/jobs/{job_b.id}", other_student).status_code == 200
    assert env.req(f"/jobs/{job_b.id}/eligibility", other_student).json()["status"] == "NO_RULE"
    assert env.req(f"/jobs/{job_b.id}", env.student).status_code == 404


def _count(env: Env, path: str) -> int:
    statements: list[str] = []

    def listener(*args: Any) -> None:
        statements.append(str(args[2]))

    engine = env.db.get_bind()
    event.listen(engine, "before_cursor_execute", listener)
    try:
        assert env.req(path, env.student).status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", listener)
    return len(statements)


def test_list_has_no_n_plus_one(env: Env) -> None:
    env.record(1, "8", 0, "80")

    def add(n: int) -> None:
        for i in range(n):
            j = env.job(f"J{i}-{len(env.db.execute(select(JobDescription.id)).all())}", role=True)
            env.rule(j, cgpa_min=Decimal("7"), cgpa_basis=CgpaBasis.LATEST_SEMESTER,
                     department_ids=[env.dept.id])

    add(3)
    env.req("/jobs", env.student)  # warm up (creates nothing, student already exists)
    small = _count(env, "/jobs")
    add(9)
    assert len(env.req("/jobs", env.student).json()) == 12
    big = _count(env, "/jobs")
    assert big == small
