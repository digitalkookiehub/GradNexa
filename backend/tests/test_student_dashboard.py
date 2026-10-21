"""Student dashboard tests: empty/full state, gap source, isolation, role guards."""
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentResult,
    AssessmentType,
    AttemptStatus,
    College,
    InterviewResult,
    LearningPlan,
    PlanStatus,
    Resume,
    ResumeAnalysis,
    Student,
    User,
)
from tests.test_readiness_api import Env

Headers = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]
PATH = "/dashboard/student"


@pytest.fixture
def env(
    client: TestClient, db: Session, auth_headers: Headers, make_user: MakeUser,
    college: College, other_college: College,
) -> Env:
    """College A/B scenario."""
    return Env(client, db, auth_headers, make_user, college, other_college)


def dash(env: Env, user: User | None = None) -> dict[str, Any]:
    r = env.req("GET", PATH, user or env.student)
    assert r.status_code == 200, r.text
    return dict(r.json())


def compute(env: Env, user: User, role_id: int | None) -> None:
    body = {} if role_id is None else {"role_id": role_id}
    r = env.req("POST", "/readiness/compute", user, json=body)
    assert r.status_code == 201, r.text


def setup_student(env: Env, user: User) -> Student:
    row = env.student_row(user)
    env.give_score(row, env.py, 40)
    env.give_score(row, env.sql, 50)
    return row


def add_attempt(
    env: Env, student: Student, title: str, pct: str, when: datetime,
    status: AttemptStatus = AttemptStatus.SUBMITTED,
) -> int:
    a = Assessment(
        college_id=student.college_id, series_key=title, title=title,
        type=AssessmentType.TECHNICAL, created_by=env.admin.id,
    )
    env.db.add(a)
    env.db.flush()
    att = AssessmentAttempt(
        assessment_id=a.id, student_id=student.id, college_id=student.college_id,
        attempt_no=1, status=status, submitted_at=when,
    )
    env.db.add(att)
    env.db.flush()
    env.db.add(
        AssessmentResult(
            attempt_id=att.id, college_id=student.college_id, student_id=student.id,
            assessment_id=a.id, assessment_version=1, total_score=Decimal("1"),
            max_score=Decimal("2"), percentage=Decimal(pct),
        )
    )
    env.db.commit()
    return int(att.id)


def test_empty_state(env: Env) -> None:
    d = dash(env)
    assert d["profile"] == {
        "profile_complete": False, "department_name": None, "roll_number": None
    }
    assert d["rule_active"] is False
    assert d["readiness"] == {"general": None, "roles": []}
    assert d["skills"] == [] and d["top_gaps"] == [] and d["goals"] == []
    assert d["plan"] is None and d["recent_assessments"] == []
    assert d["not_implemented"] == []
    assert d["resume"] is None
    assert d["interview"] == {"completed_count": 0, "latest": None}


def test_full_state(env: Env) -> None:
    env.active_rule()
    role = env.role("Analyst")
    env.role_skills(role)
    row = setup_student(env, env.student)
    put = env.req(
        "PUT", "/students/me/career-goals", env.student,
        json=[{"career_role_id": role, "priority": 1}],
    )
    assert put.status_code == 200
    compute(env, env.student, None)
    compute(env, env.student, role)
    g = env.req("POST", "/plans/generate", env.student, json={"role_id": role})
    assert g.status_code == 201, g.text
    now = datetime.now(UTC)
    ids = [
        add_attempt(env, row, f"T{i}", f"{10 * i}.50", now - timedelta(days=7 - i))
        for i in range(1, 7)
    ]
    add_attempt(env, row, "Open", "99", now, status=AttemptStatus.IN_PROGRESS)
    d = dash(env)
    assert d["rule_active"] is True
    assert d["readiness"]["general"]["rule_version"] == 1
    assert isinstance(d["readiness"]["general"]["coverage"], float)
    (r,) = d["readiness"]["roles"]
    assert r["role_id"] == role and r["role_name"] == "Analyst"
    assert isinstance(r["overall"], float) and r["level"] is not None
    assert [s["skill_name"] for s in d["skills"]] == ["SQL", "Python"]
    assert d["skills"][0]["category_name"] == "Technical"
    assert d["skills"][0]["score"] == 50.0 and d["skills"][0]["evidence_count"] == 2
    assert d["goals"] == [{"career_role_id": role, "role_name": "Analyst", "priority": 1}]
    assert d["plan"]["role_id"] == role and d["plan"]["status"] == "ACTIVE"
    assert d["plan"]["role_name"] == "Analyst"
    assert d["plan"]["progress"]["done"] == 0 and d["plan"]["progress"]["total"] > 0
    gaps = d["top_gaps"]
    assert gaps[0]["priority"] == "HIGH" and gaps[0]["skill_name"] == "Python"
    assert gaps[0]["current"] == 40.0 and gaps[0]["required"] == 70.0 and gaps[0]["gap"] == 30.0
    order = ["HIGH", "MEDIUM", "LOW", "UNASSESSED", "NONE"]
    ranks = [order.index(x["priority"]) for x in gaps]
    assert ranks == sorted(ranks) and len(gaps) <= 5
    ra = d["recent_assessments"]
    assert [a["attempt_id"] for a in ra] == list(reversed(ids))[:5]
    assert ra[0]["assessment_title"] == "T6" and ra[0]["percentage"] == 60.5


def test_gap_source_selection(env: Env) -> None:
    env.active_rule()
    role_a, role_b, role_c = env.role("A"), env.role("B"), env.role("C")
    for rid in (role_a, role_b, role_c):
        env.role_skills(rid)
    setup_student(env, env.student)
    env.req(
        "PUT", "/students/me/career-goals", env.student,
        json=[
            {"career_role_id": role_a, "priority": 2},
            {"career_role_id": role_b, "priority": 1},
            {"career_role_id": role_c, "priority": 3},
        ],
    )
    assert dash(env)["top_gaps"] == []  # goals but nothing computed
    compute(env, env.student, role_a)  # only a lower-priority goal has gaps
    assert {g["role_id"] for g in dash(env)["top_gaps"]} == {role_a}
    compute(env, env.student, role_b)  # highest-priority goal with gaps wins
    assert {g["role_id"] for g in dash(env)["top_gaps"]} == {role_b}
    g = env.req("POST", "/plans/generate", env.student, json={"role_id": role_a})
    assert g.status_code == 201, g.text
    d = dash(env)  # active plan role wins over goals
    assert {x["role_id"] for x in d["top_gaps"]} == {role_a}
    assert {x["role_name"] for x in d["top_gaps"]} == {"A"}
    assert [r["role_id"] for r in d["readiness"]["roles"]] == [role_b, role_a]
    env.req("PUT", "/students/me/career-goals", env.student, json=[])
    for p in env.db.execute(select(LearningPlan)).scalars():
        p.status = PlanStatus.ARCHIVED
    env.db.commit()
    d = dash(env)
    assert d["top_gaps"] == [] and d["plan"] is None


def test_never_other_students_or_colleges_data(env: Env) -> None:
    env.active_rule()
    role = env.role("Analyst")
    env.role_skills(role)
    row = setup_student(env, env.student)
    compute(env, env.student, None)
    compute(env, env.student, role)
    add_attempt(env, row, "Mine", "50", datetime.now(UTC))
    for other in (env.student2, env.student_b):
        d = dash(env, other)
        assert d["readiness"] == {"general": None, "roles": []}
        assert d["skills"] == [] and d["top_gaps"] == [] and d["recent_assessments"] == []
        assert d["goals"] == [] and d["plan"] is None
    assert dash(env, env.student_b)["rule_active"] is False
    mine = dash(env)
    assert len(mine["skills"]) == 2 and len(mine["recent_assessments"]) == 1


def test_profile_fields(env: Env) -> None:
    dept = env.dept(env.a)
    row = env.student_row(env.student, dept)
    row.roll_number = "R1"
    row.graduation_year = 2027
    env.db.commit()
    assert dash(env)["profile"] == {
        "profile_complete": True, "department_name": dept.name, "roll_number": "R1"
    }


def test_role_guards(env: Env) -> None:
    for u in (env.admin, env.faculty, env.tpo, env.hod, env.super_admin):
        assert env.req("GET", PATH, u).status_code == 403
    assert env.client.get("/api/v1" + PATH).status_code == 401


def _resume(env: Env, student: Student, name: str, role_id: int | None, match: Any,
            when: datetime) -> None:
    r = Resume(
        student_id=student.id, college_id=student.college_id, original_filename=name,
        content_type="application/pdf", size_bytes=10, sha256="a" * 64,
        storage_key=f"k-{name}-{student.id}",
    )
    env.db.add(r)
    env.db.flush()
    env.db.add(
        ResumeAnalysis(
            resume_id=r.id, student_id=student.id, college_id=student.college_id,
            role_id=role_id, extractor_version="v1", extracted={},
            role_match=None if match is None else {"match_percent": match}, notes=[],
            created_at=when,
        )
    )
    env.db.commit()


def test_resume_latest_and_isolation(env: Env) -> None:
    row = env.student_row(env.student)
    other = env.student_row(env.student2)
    role_id = env.role("Analyst")
    now = datetime.now(UTC)
    _resume(env, row, "old.pdf", None, None, now - timedelta(days=2))
    _resume(env, row, "new.pdf", role_id, 72.5, now)
    _resume(env, other, "other.pdf", None, 99, now + timedelta(days=1))
    d = dash(env)
    assert d["resume"]["filename"] == "new.pdf"
    assert d["resume"]["role_name"] == "Analyst"
    assert d["resume"]["role_match_percent"] == 72.5
    assert d["resume"]["resume_id"] > 0 and d["resume"]["analyzed_at"]
    assert dash(env, env.student2)["resume"]["filename"] == "other.pdf"
    assert dash(env, env.student_b)["resume"] is None


def test_resume_without_match(env: Env) -> None:
    row = env.student_row(env.student)
    _resume(env, row, "a.pdf", None, None, datetime.now(UTC))
    d = dash(env)["resume"]
    assert d["role_name"] is None and d["role_match_percent"] is None


def test_interview_block(env: Env) -> None:
    row = env.student_row(env.student)
    other = env.student_row(env.student2)
    r1 = env.role("Analyst")
    r2 = env.role("Engineer")
    now = datetime.now(UTC)
    from app.models import InterviewStatus, MockInterview

    def add(student: Student, role: int, overall: str | None, when: datetime) -> None:
        iv = MockInterview(
            student_id=student.id, college_id=student.college_id, role_id=role,
            status=InterviewStatus.COMPLETED,
        )
        env.db.add(iv)
        env.db.flush()
        env.db.add(
            InterviewResult(
                interview_id=iv.id, college_id=student.college_id, student_id=student.id,
                role_id=role, overall=None if overall is None else Decimal(overall),
                competency_scores=[], per_question=[], scoring_version="rubric-1",
                computed_at=when,
            )
        )
        env.db.commit()

    add(row, r1, "40", now - timedelta(days=1))
    add(row, r2, "65.5", now)
    add(other, r1, "99", now + timedelta(days=1))
    d = dash(env)["interview"]
    assert d["completed_count"] == 2
    assert d["latest"]["role_name"] == "Engineer" and d["latest"]["overall"] == 65.5
    assert dash(env, env.student_b)["interview"] == {"completed_count": 0, "latest": None}
