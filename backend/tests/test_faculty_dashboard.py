"""Faculty dashboard tests: assigned-only visibility, needs_support rules, query bound."""
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AttemptStatus,
    AuditLog,
    College,
    FacultyAssignment,
    GapPriority,
    GapStatus,
    Student,
    User,
    UserRole,
)
from tests.test_hod_dashboard import T0, World, count_statements

Headers = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]
URL = "/api/v1/dashboard/faculty"


@pytest.fixture
def world(
    db: Session, college: College, other_college: College, make_user: MakeUser
) -> World:
    return World(db, make_user, college, other_college)


def assign(world: World, faculty: User, *students: Student) -> None:
    for s in students:
        world.db.add(
            FacultyAssignment(
                college_id=faculty.college_id, faculty_user_id=faculty.id, student_id=s.id
            )
        )
    world.db.commit()


def get(client: TestClient, h: Headers, user: User) -> Any:
    return client.get(URL, headers=h(user))


def build(world: World) -> dict[str, Student]:
    """Five students for faculty 1, one for faculty 2 and one unassigned."""
    cs = world.cs
    s1 = world.student(world.a, cs, complete=True, name="Zara")
    s2 = world.student(world.a, cs, name="Amy")
    s3 = world.student(world.a, cs, name="Other Faculty Student")
    s4 = world.student(world.a, None, name="Bob")  # null overall
    s5 = world.student(world.a, cs, name="Cy")  # no score
    s6 = world.student(world.a, cs, name="Healthy")
    s7 = world.student(world.a, cs, name="Unassigned Nobody")
    world.score(s1, 85, "Strong", 100, age=5)
    world.score(s1, 40, "Foundation", 30, age=0)
    old = world.score(s1, 10, "Foundation", 10, role=world.r1, age=1)
    world.gap(old, world.logic, GapStatus.GAP, GapPriority.HIGH)  # superseded
    new = world.score(s1, 20, "Foundation", 10, role=world.r1, age=6)
    world.gap(new, world.py, GapStatus.GAP, GapPriority.HIGH)
    world.gap(new, world.sql, GapStatus.GAP, GapPriority.LOW)
    r2s = world.score(s1, 20, "Foundation", 10, role=world.r2, age=3)
    world.gap(r2s, world.py, GapStatus.GAP, GapPriority.HIGH)  # same skill, 2nd role
    world.score(s2, 60, "Developing", 50)
    s2r = world.score(s2, 30, "Foundation", 10, role=world.r1)
    world.gap(s2r, world.py, GapStatus.GAP, GapPriority.HIGH)
    world.gap(s2r, world.sql, GapStatus.GAP, GapPriority.HIGH)
    world.score(s3, 20, "Foundation", 20)
    s3r = world.score(s3, 20, "Foundation", 10, role=world.r1)
    world.gap(s3r, world.sql, GapStatus.GAP, GapPriority.HIGH)
    world.score(s4, None, None, 0)
    world.score(s6, 75, "Developing", 80)
    s6r = world.score(s6, 75, "Developing", 80, role=world.r1)
    world.gap(s6r, world.sql, GapStatus.GAP, GapPriority.MEDIUM)
    s7r = world.score(s7, 20, "Foundation", 10, role=world.r1)
    world.gap(s7r, world.sql, GapStatus.GAP, GapPriority.HIGH)
    q = world.assessment(world.a, title="Quiz A")
    q2 = world.assessment(world.a, title="Quiz B")
    world.attempt(q, s1, no=1, pct=50, when=T0 + timedelta(days=2))
    world.attempt(q, s1, no=2, pct=90, when=T0 + timedelta(days=9))
    world.attempt(q2, s2, no=1, pct=70, when=T0 + timedelta(days=4))
    world.attempt(q, s2, AttemptStatus.IN_PROGRESS, no=1)
    world.attempt(q, s3, no=1, pct=10, when=T0 + timedelta(days=4))  # not assigned
    world.attempt(q, s7, no=1, pct=10, when=T0 + timedelta(days=4))  # not assigned
    assign(world, world.faculty, s1, s2, s4, s5, s6)
    assign(world, world.faculty2, s3)
    return {"s1": s1, "s2": s2, "s3": s3, "s4": s4, "s5": s5, "s6": s6, "s7": s7}


def test_assigned_students_only_and_rules(
    world: World, client: TestClient, auth_headers: Headers
) -> None:
    st = build(world)
    r = get(client, auth_headers, world.faculty)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["totals"] == {"assigned_students": 5, "with_readiness_score": 4, "needing_support": 4}
    names = [s["name"] for s in b["students"]]
    # needs_support first (by name), then the rest
    assert names == ["Amy", "Bob", "Cy", "Zara", "Healthy"]
    assert "Other Faculty Student" not in r.text
    assert "Unassigned Nobody" not in r.text
    ids = {s["student_id"] for s in b["students"]}
    assert st["s3"].id not in ids and st["s7"].id not in ids
    by = {s["name"]: s for s in b["students"]}
    assert by["Zara"] == {
        "student_id": st["s1"].id, "name": "Zara", "email": by["Zara"]["email"],
        "department_name": "Computer Science", "roll_number": st["s1"].roll_number,
        "overall": 85.0, "level": "Strong", "coverage": 100.0,
        "high_priority_gap_count": 1,  # py only (distinct skill, latest sets only)
        "last_assessment_percentage": 90.0,
        "last_assessment_at": by["Zara"]["last_assessment_at"],
        "needs_support": True, "support_reasons": ["1 high-priority skill gap"],
    }
    assert by["Zara"]["last_assessment_at"] is not None
    assert by["Amy"]["support_reasons"] == ["2 high-priority skill gaps"]
    assert by["Amy"]["last_assessment_percentage"] == 70.0
    assert by["Bob"]["support_reasons"] == ["Not enough evidence yet"]
    assert by["Bob"]["overall"] is None and by["Bob"]["department_name"] is None
    assert by["Cy"]["support_reasons"] == ["No readiness score yet"]
    assert by["Cy"]["overall"] is None and by["Cy"]["level"] is None
    assert by["Cy"]["coverage"] is None and by["Cy"]["last_assessment_at"] is None
    assert by["Healthy"]["needs_support"] is False
    assert by["Healthy"]["support_reasons"] == []
    assert by["Healthy"]["high_priority_gap_count"] == 0  # medium gap only
    assert [(g["skill_name"], g["students_affected"], g["high_priority_students"])
            for g in b["top_gaps"]] == [("SQL", 3, 1), ("Python", 2, 2)]
    assert b["assessment_performance"] == [
        {"assessment_id": b["assessment_performance"][0]["assessment_id"], "title": "Quiz A",
         "attempts_submitted": 2, "average_percentage": 70.0},
        {"assessment_id": b["assessment_performance"][1]["assessment_id"], "title": "Quiz B",
         "attempts_submitted": 1, "average_percentage": 70.0},
    ]


def test_second_faculty_sees_only_theirs(
    world: World, client: TestClient, auth_headers: Headers
) -> None:
    build(world)
    b = get(client, auth_headers, world.faculty2).json()
    assert [s["name"] for s in b["students"]] == ["Other Faculty Student"]
    assert b["assessment_performance"][0]["attempts_submitted"] == 1


def test_no_assignments(world: World, client: TestClient, auth_headers: Headers) -> None:
    b = get(client, auth_headers, world.faculty).json()
    assert b["totals"] == {"assigned_students": 0, "with_readiness_score": 0, "needing_support": 0}
    assert b["students"] == [] and b["top_gaps"] == [] and b["assessment_performance"] == []


@pytest.mark.parametrize(
    "role",
    [UserRole.TPO, UserRole.ADMIN, UserRole.HOD, UserRole.STUDENT, UserRole.SUPER_ADMIN],
)
def test_role_guards(
    world: World, client: TestClient, auth_headers: Headers, make_user: MakeUser,
    role: UserRole,
) -> None:
    user = make_user(world.a, role, email=f"g-{role.value}@x.test")
    assert get(client, auth_headers, user).status_code == 403
    assert client.get(URL).status_code == 401


def test_cross_college_assignment_is_ignored(
    world: World, client: TestClient, auth_headers: Headers, db: Session
) -> None:
    sb = world.student(world.b, None, name="College B Kid")
    world.score(sb, 50, "Developing", 50)
    # A stray assignment row pointing at a college B student must expose nothing.
    db.add(
        FacultyAssignment(
            college_id=world.a.id, faculty_user_id=world.faculty.id, student_id=sb.id
        )
    )
    db.commit()
    r = get(client, auth_headers, world.faculty)
    assert r.json()["students"] == []
    assert "College B Kid" not in r.text


def test_audit_row(
    world: World, client: TestClient, auth_headers: Headers, db: Session
) -> None:
    get(client, auth_headers, world.faculty)
    rows = db.execute(
        select(AuditLog).where(AuditLog.action == "DASHBOARD_FACULTY_READ")
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].user_id == world.faculty.id and rows[0].college_id == world.a.id


def test_statement_count_is_bounded(
    world: World, client: TestClient, auth_headers: Headers, db: Session
) -> None:
    def add(n: int) -> None:
        for i in range(n):
            st = world.student(world.a, world.cs, complete=True)
            world.score(st, 50 + i, "Developing", 40)
            sc = world.score(st, 20, "Foundation", 10, role=world.r1)
            world.gap(sc, world.py, GapStatus.GAP, GapPriority.HIGH)
            world.attempt(world.assessment(world.a), st, pct=60, when=T0 + timedelta(days=i))
            assign(world, world.faculty, st)

    def run() -> None:
        assert get(client, auth_headers, world.faculty).status_code == 200

    add(3)
    small = count_statements(db, run)
    add(9)
    large = count_statements(db, run)
    assert small == large
    assert large < 20
