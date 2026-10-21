"""Placement analytics tests: role readiness, eligibility counts, trends, guards, privacy."""
import json
from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AcademicRecord,
    AuditLog,
    CgpaBasis,
    College,
    GapPriority,
    GapStatus,
    JobStatus,
    Student,
    User,
    UserRole,
)
from app.services import eligibility_engine as engine
from tests.test_hod_dashboard import World, count_statements

Headers = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]
URL = "/api/v1/dashboard/placement/analytics"


@pytest.fixture
def world(
    db: Session, college: College, other_college: College, make_user: MakeUser
) -> World:
    return World(db, make_user, college, other_college)


def get(client: TestClient, h: Headers, user: User, **params: Any) -> Any:
    return client.get(URL, headers=h(user), params=params)


def record(world: World, st: Student, sem: int, cgpa: str, arrears: int = 0) -> None:
    world.db.add(
        AcademicRecord(
            student_id=st.id, college_id=st.college_id, semester=sem, cgpa=Decimal(cgpa),
            active_arrears=arrears, attendance_pct=Decimal("90"),
        )
    )
    world.db.commit()


def test_role_readiness(world: World, client: TestClient, auth_headers: Headers) -> None:
    s1 = world.student(world.a, world.cs)
    s2 = world.student(world.a, world.cs)
    s3 = world.student(world.a, world.ec)
    s4 = world.student(world.a, world.ec)
    for st, role in ((s1, world.r1), (s2, world.r1), (s3, world.r1), (s1, world.r2),
                     (s2, world.r2)):
        world.goal(st, role, 1 if role == world.r1 else 2)
    world.score(s1, 10, "Foundation", 99, role=world.r1, age=1)  # superseded
    world.score(s1, 20, "Foundation", 10, role=world.r1, age=2)
    world.score(s2, 30, "Foundation", 10, role=world.r1)
    world.score(s3, 30, "Foundation", 10, role=world.r1)
    world.score(s1, 20, "Foundation", 10, role=world.r2)
    world.score(s2, None, None, 0, role=world.r2)  # goal but no evidence
    world.score(s4, 90, "Strong", 90, role=world.r2)  # score without a goal: excluded
    world.score(s1, 77, "Strong", 77)  # general score: not role readiness
    body = get(client, auth_headers, world.tpo).json()
    assert body["role_readiness"] == [
        {"role_id": world.r1.id, "role_name": "Role One", "students_with_goal": 3,
         "students_scored": 3, "average_overall": 26.67, "average_coverage": 10.0},
        {"role_id": world.r2.id, "role_name": "Role Two", "students_with_goal": 2,
         "students_scored": 1, "average_overall": 20.0, "average_coverage": 10.0},
    ]
    cs = get(client, auth_headers, world.admin, department_id=world.cs.id).json()
    assert body["scope"] == {"department_id": None, "department_name": None}
    assert cs["scope"] == {"department_id": world.cs.id, "department_name": "Computer Science"}
    assert cs["role_readiness"][0]["students_with_goal"] == 2
    assert cs["role_readiness"][0]["average_overall"] == 25.0


def test_role_readiness_limited_to_15(
    world: World, client: TestClient, auth_headers: Headers
) -> None:
    st = world.student(world.a, world.cs)
    for i in range(17):
        world.goal(st, world.role(world.a, f"Extra {i:02d}"), i + 1)
    assert len(get(client, auth_headers, world.tpo).json()["role_readiness"]) == 15


def test_company_eligibility_matches_engine(
    world: World, client: TestClient, auth_headers: Headers
) -> None:
    ok = world.student(world.a, world.cs, grad=2027)
    low = world.student(world.a, world.cs, grad=2027)
    none = world.student(world.a, world.ec, grad=2027)  # no academic records
    record(world, ok, 1, "6.00")
    record(world, ok, 2, "8.00")
    record(world, low, 1, "9.00")
    record(world, low, 2, "6.50")
    other = world.student(world.a, world.me, grad=2027)
    record(world, other, 1, "9.50")
    cg = {"cgpa_min": Decimal("7.00"), "cgpa_basis": CgpaBasis.LATEST_SEMESTER}
    j1 = world.job(world.a, "Cgpa Job", deadline=date(2026, 3, 1), rule=cg)
    j_dept = world.job(
        world.a, "Dept Job", deadline=date(2026, 2, 1),
        rule={"department_ids": [world.cs.id]},
    )
    j_norule = world.job(world.a, "No Rule Job", deadline=None)
    j_notes = world.job(world.a, "Notes Job", deadline=date(2026, 4, 1),
                        rule={"custom_notes": ["bring id"]})
    world.job(world.a, "Closed Job", status=JobStatus.CLOSED, rule=cg)
    world.job(world.a, "Draft Job", status=JobStatus.DRAFT, rule=cg)
    b = get(client, auth_headers, world.tpo).json()
    assert [j["job_id"] for j in b["company_eligibility"]] == [
        j_dept.id, j1.id, j_notes.id, j_norule.id,
    ]
    by = {j["job_title"]: j for j in b["company_eligibility"]}
    assert by["Cgpa Job"] == {
        "job_id": j1.id, "job_title": "Cgpa Job", "company_name": "Co Cgpa Job",
        "eligible": 2, "not_eligible": 1, "incomplete_data": 1, "no_rule_students": 0,
    }
    assert by["Dept Job"]["eligible"] == 2
    assert by["Dept Job"]["not_eligible"] == 2
    assert by["Dept Job"]["incomplete_data"] == 0
    for title in ("No Rule Job", "Notes Job"):
        assert by[title]["no_rule_students"] == 4
        assert by[title]["eligible"] == by[title]["not_eligible"] == 0
    # engine cross-check for the CGPA job
    expect = {engine.ELIGIBLE: 0, engine.NOT_ELIGIBLE: 0, engine.INCOMPLETE_DATA: 0}
    rule = engine.RuleInput(cgpa_min=Decimal("7.00"), cgpa_basis=engine.LATEST_SEMESTER)
    for recs in ([(1, "6.00"), (2, "8.00")], [(1, "9.00"), (2, "6.50")], [], [(1, "9.50")]):
        facts = engine.StudentFacts(
            None, None, [engine.RecordFact(s, Decimal(c), 0, Decimal("90")) for s, c in recs]
        )
        expect[engine.evaluate(rule, facts).status] += 1
    assert (by["Cgpa Job"]["eligible"], by["Cgpa Job"]["not_eligible"],
            by["Cgpa Job"]["incomplete_data"]) == (
        expect[engine.ELIGIBLE], expect[engine.NOT_ELIGIBLE], expect[engine.INCOMPLETE_DATA]
    )
    # department scope narrows the students counted (cs only: ok + low)
    cs = get(client, auth_headers, world.tpo, department_id=world.cs.id).json()
    cs_by = {j["job_title"]: j for j in cs["company_eligibility"]}
    assert cs_by["Cgpa Job"]["eligible"] == 1 and cs_by["Cgpa Job"]["not_eligible"] == 1
    assert cs_by["Cgpa Job"]["incomplete_data"] == 0
    assert cs_by["No Rule Job"]["no_rule_students"] == 2
    assert none.id != ok.id


def test_average_basis_and_limit_of_20_jobs(
    world: World, client: TestClient, auth_headers: Headers
) -> None:
    st = world.student(world.a, world.cs)
    record(world, st, 1, "5.00")
    record(world, st, 2, "9.00")
    avg = {"cgpa_min": Decimal("7.00"), "cgpa_basis": CgpaBasis.AVERAGE_ALL_SEMESTERS}
    world.job(world.a, "Avg", deadline=date(2026, 1, 1), rule=avg)
    for i in range(22):
        world.job(world.a, f"J{i:02d}", deadline=date(2026, 6, 1) + timedelta(days=i))
    jobs = get(client, auth_headers, world.tpo).json()["company_eligibility"]
    assert len(jobs) == 20
    assert jobs[0]["job_title"] == "Avg" and jobs[0]["eligible"] == 1


def test_progress_trends(world: World, client: TestClient, auth_headers: Headers) -> None:
    s1 = world.student(world.a, world.cs)
    s2 = world.student(world.a, world.cs)
    s3 = world.student(world.a, world.ec)
    world.score(s1, 40, "Foundation", 30, age=0)
    world.score(s1, 60, "Developing", 60, age=10)  # latest in January
    world.score(s1, 85, "Strong", 90, age=40)  # February
    world.score(s2, 50, "Developing", 50, age=2)
    world.score(s3, None, None, 0, age=41)  # February, no overall
    world.score(s1, 5, "Foundation", 5, role=world.r1, age=45)  # role score: ignored
    body = get(client, auth_headers, world.tpo).json()
    assert body["progress_trends"] == [
        {"month": "2026-01", "students_scored": 2, "average_overall": 55.0},
        {"month": "2026-02", "students_scored": 1, "average_overall": 85.0},
    ]
    cs = get(client, auth_headers, world.tpo, department_id=world.ec.id).json()
    assert cs["progress_trends"] == []


def test_trends_limited_to_12_months(
    world: World, client: TestClient, auth_headers: Headers
) -> None:
    st = world.student(world.a, world.cs)
    for i in range(14):
        world.score(st, 50, "Developing", 50, age=i * 31)
    months = [p["month"] for p in get(client, auth_headers, world.tpo).json()["progress_trends"]]
    assert len(months) == 12 and months == sorted(months)


def test_guards_and_404(
    world: World, client: TestClient, auth_headers: Headers, make_user: MakeUser
) -> None:
    for role in (UserRole.HOD, UserRole.FACULTY, UserRole.STUDENT, UserRole.SUPER_ADMIN):
        user = make_user(world.a, role, email=f"g-{role.value}@x.test")
        assert get(client, auth_headers, user).status_code == 403
    assert client.get(URL).status_code == 401
    foreign = world.dept(world.b, "XX", "Foreign")
    r = get(client, auth_headers, world.tpo, department_id=foreign.id)
    assert r.status_code == 404
    assert r.json() == {"detail": "Department not found"}
    assert get(client, auth_headers, world.tpo, department_id=99999).status_code == 404


def test_aggregates_only_and_cross_college(
    world: World, client: TestClient, auth_headers: Headers
) -> None:
    world.populate()
    st = world.student(world.a, world.cs, grad=2027)
    record(world, st, 1, "8.00")
    world.job(world.a, "Job", rule={"cgpa_min": Decimal("7"), "cgpa_basis": CgpaBasis.LATEST_SEMESTER})
    sb = world.student(world.b, None, complete=True)
    world.goal(sb, world.role(world.b, "B role"))
    world.score(sb, 99, "Strong", 99)
    world.job(world.b, "B Job", rule={"max_arrears": 0})
    raw = get(client, auth_headers, world.tpo).text
    assert "@" not in raw and "pupil" not in raw.lower()
    keys: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            keys.update(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(json.loads(raw))
    assert not keys & {"email", "full_name", "student_id", "user_id", "roll_number", "name"}
    assert "B Job" not in raw and "B role" not in raw
    b = get(client, auth_headers, world.tpo_b).json()
    assert [j["job_title"] for j in b["company_eligibility"]] == ["B Job"]
    assert b["company_eligibility"][0]["incomplete_data"] == 1
    assert [r["role_name"] for r in b["role_readiness"]] == ["B role"]
    assert len(b["progress_trends"]) == 1
    resp = get(client, auth_headers, world.admin_b)
    assert resp.status_code == 200, resp.text
    empty = resp.json()
    assert empty["progress_trends"][0]["students_scored"] == 1


def test_empty_college(world: World, client: TestClient, auth_headers: Headers) -> None:
    b = get(client, auth_headers, world.tpo_b).json()
    assert b["role_readiness"] == [] and b["company_eligibility"] == []
    assert b["progress_trends"] == []


def test_audit_row(
    world: World, client: TestClient, auth_headers: Headers, db: Session
) -> None:
    get(client, auth_headers, world.tpo)
    get(client, auth_headers, world.admin, department_id=world.cs.id)
    rows = db.execute(
        select(AuditLog).where(AuditLog.action == "DASHBOARD_PLACEMENT_ANALYTICS_READ")
    ).scalars().all()
    assert len(rows) == 2
    assert {r.user_id for r in rows} == {world.tpo.id, world.admin.id}


def test_statement_count_is_bounded(
    world: World, client: TestClient, auth_headers: Headers, db: Session
) -> None:
    world.job(world.a, "Job", rule={"cgpa_min": Decimal("7"), "cgpa_basis": CgpaBasis.LATEST_SEMESTER})

    def add(n: int) -> None:
        for i in range(n):
            st = world.student(world.a, world.cs, grad=2027)
            record(world, st, 1, "8.00")
            world.goal(st, world.r1)
            world.score(st, 50 + i, "Developing", 40, age=i * 20)
            world.score(st, 20, "Foundation", 10, role=world.r1)
            sc = world.score(st, 20, "Foundation", 10, role=world.r1, age=1)
            world.gap(sc, world.py, GapStatus.GAP, GapPriority.HIGH)

    def run() -> None:
        assert get(client, auth_headers, world.tpo).status_code == 200

    add(3)
    small = count_statements(db, run)
    add(9)
    large = count_statements(db, run)
    assert small == large
    assert large < 20
