"""Placement officer dashboard tests: aggregates, scoping, guards, privacy, query bound."""
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentStatus,
    AssessmentType,
    AttemptStatus,
    AuditLog,
    CareerRole,
    College,
    Department,
    GapPriority,
    GapStatus,
    ReadinessRule,
    ReadinessScore,
    Skill,
    SkillCategory,
    SkillGap,
    Student,
    User,
    UserRole,
)

Headers = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]
URL = "/api/v1/dashboard/placement"
T0 = datetime(2026, 1, 1, tzinfo=UTC)


class World:
    """Hand-built dataset for college A plus some foreign data in college B."""

    def __init__(self, db: Session, make_user: MakeUser, a: College, b: College) -> None:
        self.db, self.make_user, self.a, self.b = db, make_user, a, b
        self.admin = make_user(a, UserRole.ADMIN)
        self.tpo = make_user(a, UserRole.TPO)
        self.tpo_b = make_user(b, UserRole.TPO)
        self.cs = self.dept(a, "CS", "Computer Science")
        self.ec = self.dept(a, "EC", "Electronics")
        cat = SkillCategory(college_id=a.id, name="Tech")
        db.add(cat)
        db.commit()
        self.py = self.skill(a, cat, "Python")
        self.sql = self.skill(a, cat, "SQL")
        self.logic = self.skill(a, cat, "Logic")
        self.r1 = self.role(a, "Role One")
        self.r2 = self.role(a, "Role Two")
        self.rule1 = self.rule(a, 1, False)
        self.rule2 = self.rule(a, 2, True)
        self.n = 0

    def dept(self, college: College, code: str, name: str) -> Department:
        obj = Department(college_id=college.id, name=name, code=code)
        self.db.add(obj)
        self.db.commit()
        return obj

    def skill(self, college: College, cat: SkillCategory, name: str) -> Skill:
        obj = Skill(college_id=college.id, category_id=cat.id, name=name)
        self.db.add(obj)
        self.db.commit()
        return obj

    def role(self, college: College, name: str) -> CareerRole:
        obj = CareerRole(college_id=college.id, name=name)
        self.db.add(obj)
        self.db.commit()
        return obj

    def rule(self, college: College, version: int, active: bool) -> ReadinessRule:
        obj = ReadinessRule(
            college_id=college.id, version=version, weights={"1": 100},
            level_thresholds=[
                {"level": "Foundation", "min_score": 0},
                {"level": "Developing", "min_score": 50},
                {"level": "Strong", "min_score": 80},
            ],
            gap_thresholds={"high_min_gap": 30, "medium_min_gap": 15},
            is_active=active, created_by=self.admin.id,
        )
        self.db.add(obj)
        self.db.commit()
        return obj

    def student(
        self, college: College, dept: Department | None = None, complete: bool = False,
        grad: bool = False,
    ) -> Student:
        self.n += 1
        user = self.make_user(college, UserRole.STUDENT, email=f"stu{self.n}@x{college.id}.test")
        row = Student(
            user_id=user.id, college_id=college.id,
            department_id=dept.id if dept else None,
            roll_number=f"R{self.n}" if (complete or grad) else None,
            graduation_year=2027 if complete else None,
        )
        self.db.add(row)
        self.db.commit()
        return row

    def score(
        self, st: Student, overall: float | None, level: str | None, cov: float,
        version: int = 2, role: CareerRole | None = None, age: int = 0,
    ) -> ReadinessScore:
        rule = self.rule1 if version == 1 else self.rule2
        obj = ReadinessScore(
            student_id=st.id, college_id=st.college_id,
            role_id=role.id if role else None, rule_id=rule.id, rule_version=version,
            overall=None if overall is None else Decimal(str(overall)), level=level,
            coverage=Decimal(str(cov)), computed_at=T0 + timedelta(days=age),
        )
        self.db.add(obj)
        self.db.commit()
        return obj

    def gap(
        self, sc: ReadinessScore, skill: Skill, status: GapStatus, prio: GapPriority
    ) -> None:
        assert sc.role_id is not None
        self.db.add(
            SkillGap(
                student_id=sc.student_id, college_id=sc.college_id, role_id=sc.role_id,
                skill_id=skill.id, readiness_score_id=sc.id, required=Decimal("70"),
                status=status, priority=prio, recommended_action="x",
            )
        )
        self.db.commit()

    def assessment(
        self, college: College, status: AssessmentStatus, dept: Department | None = None
    ) -> Assessment:
        self.n += 1
        obj = Assessment(
            college_id=college.id, series_key=f"s{self.n}", title="Quiz",
            type=AssessmentType.TECHNICAL, department_id=dept.id if dept else None,
            status=status, created_by=self.admin.id,
        )
        self.db.add(obj)
        self.db.commit()
        return obj

    def attempt(
        self, a: Assessment, st: Student, status: AttemptStatus, no: int = 1
    ) -> None:
        self.db.add(
            AssessmentAttempt(
                assessment_id=a.id, student_id=st.id, college_id=st.college_id,
                attempt_no=no, status=status,
            )
        )
        self.db.commit()

    def populate(self) -> None:
        s1 = self.student(self.a, self.cs, complete=True)
        s2 = self.student(self.a, self.cs, grad=True)  # roll but no grad year: incomplete
        s3 = self.student(self.a, self.ec)
        s4 = self.student(self.a, None)
        self.student(self.a, self.ec)  # s5: no score at all
        self.score(s1, 40, "Foundation", 30, version=1, age=0)
        self.score(s1, 85, "Strong", 100, age=5)
        self.score(s2, 60, "Developing", 50)
        self.score(s3, 30, "Foundation", 20, version=1)
        self.score(s4, None, None, 0)
        # Role scores must not affect the general distribution.
        self.score(s1, 10, "Foundation", 10, role=self.r1, age=1)
        old = self.score(s1, 10, "Foundation", 10, role=self.r1, age=2)
        self.gap(old, self.logic, GapStatus.GAP, GapPriority.HIGH)  # superseded set
        new = self.score(s1, 20, "Foundation", 10, role=self.r1, age=6)
        self.gap(new, self.py, GapStatus.GAP, GapPriority.HIGH)
        self.gap(new, self.sql, GapStatus.GAP, GapPriority.LOW)
        r2s = self.score(s1, 20, "Foundation", 10, role=self.r2, age=3)
        self.gap(r2s, self.py, GapStatus.GAP, GapPriority.MEDIUM)  # same student, 2nd role
        s2r = self.score(s2, 30, "Foundation", 10, role=self.r1)
        self.gap(s2r, self.py, GapStatus.GAP, GapPriority.HIGH)
        self.gap(s2r, self.sql, GapStatus.READY, GapPriority.NONE)
        s3r = self.score(s3, 30, "Foundation", 10, role=self.r1)
        self.gap(s3r, self.sql, GapStatus.GAP, GapPriority.HIGH)
        self.gap(s3r, self.logic, GapStatus.NO_EVIDENCE, GapPriority.UNASSESSED)
        pub_all = self.assessment(self.a, AssessmentStatus.PUBLISHED)
        self.assessment(self.a, AssessmentStatus.PUBLISHED, self.cs)
        self.assessment(self.a, AssessmentStatus.PUBLISHED, self.ec)
        self.assessment(self.a, AssessmentStatus.DRAFT)
        self.attempt(pub_all, s1, AttemptStatus.SUBMITTED, 1)
        self.attempt(pub_all, s1, AttemptStatus.SUBMITTED, 2)
        self.attempt(pub_all, s2, AttemptStatus.IN_PROGRESS, 1)

    def populate_foreign(self) -> None:
        sb = self.student(self.b, None, complete=True)
        self.score(sb, 99, "Strong", 99)
        sc = self.score(sb, 50, "Developing", 50, role=self.role(self.b, "B role"))
        self.gap(sc, self.py, GapStatus.GAP, GapPriority.HIGH)  # even a cross-college skill id
        self.attempt(self.assessment(self.b, AssessmentStatus.PUBLISHED), sb,
                     AttemptStatus.SUBMITTED)


@pytest.fixture
def world(
    db: Session, college: College, other_college: College, make_user: MakeUser
) -> World:
    return World(db, make_user, college, other_college)


def get(
    client: TestClient, h: Headers, user: User, **params: Any
) -> Any:
    return client.get(URL, headers=h(user), params=params)


def test_aggregates(world: World, client: TestClient, auth_headers: Headers) -> None:
    world.populate()
    r = get(client, auth_headers, world.tpo)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scope"] == {"department_id": None, "department_name": None}
    assert body["rule"] == {"id": world.rule2.id, "version": 2}
    assert body["rule_versions_in_use"] == [1, 2]
    assert body["totals"] == {
        "students": 5, "profile_complete": 1, "with_readiness_score": 4,
        "with_assessment_submitted": 1,
    }
    assert body["level_distribution"] == [
        {"level": "Strong", "count": 1},
        {"level": "Developing", "count": 1},
        {"level": "Foundation", "count": 1},
        {"level": None, "count": 2},
    ]
    names = [d["department_name"] for d in body["departments"]]
    assert names == sorted(names)
    by_name = {d["department_name"]: d for d in body["departments"]}
    assert by_name["Computer Science"]["avg_overall"] == 72.5
    assert by_name["Computer Science"]["avg_coverage"] == 75.0
    assert by_name["Electronics"]["scored"] == 1
    assert by_name["Electronics"]["students"] == 2
    assert by_name["Unassigned"] == {
        "department_id": None, "department_name": "Unassigned", "students": 1,
        "scored": 0, "avg_overall": None, "avg_coverage": None,
    }
    assert body["top_gaps"] == [
        {"skill_id": world.py.id, "skill_name": "Python", "students_affected": 2,
         "high_priority_students": 2},
        {"skill_id": world.sql.id, "skill_name": "SQL", "students_affected": 2,
         "high_priority_students": 1},
    ]
    assert body["assessment_participation"] == {
        "published_assessments": 3, "students_with_attempts": 2, "submitted_attempts": 2,
    }
    assert isinstance(body["departments"][0]["avg_overall"], float)


def test_department_filter(world: World, client: TestClient, auth_headers: Headers) -> None:
    world.populate()
    body = get(client, auth_headers, world.admin, department_id=world.cs.id).json()
    assert body["scope"] == {"department_id": world.cs.id, "department_name": "Computer Science"}
    assert body["totals"]["students"] == 2
    assert [d["department_name"] for d in body["departments"]] == ["Computer Science"]
    assert body["rule_versions_in_use"] == [2]
    assert body["level_distribution"] == [
        {"level": "Strong", "count": 1}, {"level": "Developing", "count": 1},
    ]
    assert body["top_gaps"] == [
        {"skill_id": world.py.id, "skill_name": "Python", "students_affected": 2,
         "high_priority_students": 2},
        {"skill_id": world.sql.id, "skill_name": "SQL", "students_affected": 1,
         "high_priority_students": 0},
    ]
    # CS-specific + college-wide published assessments (not the EC one).
    assert body["assessment_participation"]["published_assessments"] == 2


def test_foreign_department_404(
    world: World, client: TestClient, auth_headers: Headers
) -> None:
    foreign = world.dept(world.b, "XX", "Foreign")
    r = get(client, auth_headers, world.tpo, department_id=foreign.id)
    assert r.status_code == 404
    assert r.json() == {"detail": "Department not found"}
    assert get(client, auth_headers, world.tpo, department_id=99999).status_code == 404


@pytest.mark.parametrize(
    "role", [UserRole.HOD, UserRole.FACULTY, UserRole.STUDENT, UserRole.SUPER_ADMIN]
)
def test_role_guards(
    world: World, client: TestClient, auth_headers: Headers, make_user: MakeUser,
    role: UserRole,
) -> None:
    user = make_user(world.a, role, email=f"guard-{role.value}@x.test")
    assert get(client, auth_headers, user).status_code == 403
    assert client.get(URL).status_code == 401


def test_no_identifiers_in_body(
    world: World, client: TestClient, auth_headers: Headers
) -> None:
    world.populate()
    raw = get(client, auth_headers, world.tpo).text
    assert "@" not in raw
    assert "stu" not in raw.lower().replace("students", "")
    assert "user" not in raw.lower().replace("students", "")
    forbidden = {"email", "full_name", "student_id", "user_id", "roll_number", "name"}
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
    assert not keys & forbidden


def test_cross_college_isolation(
    world: World, client: TestClient, auth_headers: Headers
) -> None:
    world.populate()
    world.populate_foreign()
    a = get(client, auth_headers, world.tpo).json()
    assert a["totals"]["students"] == 5
    assert a["assessment_participation"]["students_with_attempts"] == 2
    assert a["top_gaps"][0]["students_affected"] == 2
    b = get(client, auth_headers, world.tpo_b).json()
    assert b["rule"] is None
    assert b["totals"] == {
        "students": 1, "profile_complete": 0, "with_readiness_score": 1,
        "with_assessment_submitted": 1,
    }
    assert b["level_distribution"] == [{"level": "Strong", "count": 1}]
    assert b["rule_versions_in_use"] == [2]
    # Foreign college's gap rows reference college A's skill: must not leak.
    assert b["top_gaps"] == []
    assert b["assessment_participation"] == {
        "published_assessments": 1, "students_with_attempts": 1, "submitted_attempts": 1,
    }
    assert [d["department_name"] for d in b["departments"]] == ["Unassigned"]


def test_empty_college(world: World, client: TestClient, auth_headers: Headers) -> None:
    body = get(client, auth_headers, world.tpo_b).json()
    assert body["rule"] is None
    assert body["rule_versions_in_use"] == []
    assert body["totals"] == {
        "students": 0, "profile_complete": 0, "with_readiness_score": 0,
        "with_assessment_submitted": 0,
    }
    assert body["level_distribution"] == []
    assert body["departments"] == []
    assert body["top_gaps"] == []
    assert body["assessment_participation"] == {
        "published_assessments": 0, "students_with_attempts": 0, "submitted_attempts": 0,
    }


def test_levels_not_in_rule_sorted_after(
    world: World, client: TestClient, auth_headers: Headers
) -> None:
    s1 = world.student(world.a, world.cs)
    s2 = world.student(world.a, world.cs)
    s3 = world.student(world.a, world.cs)
    world.score(s1, 90, "Zeta", 10)
    world.score(s2, 90, "Alpha", 10)
    world.score(s3, 90, "Strong", 10)
    levels = get(client, auth_headers, world.tpo).json()["level_distribution"]
    assert [x["level"] for x in levels] == ["Strong", "Alpha", "Zeta"]


def test_top_gaps_limited_to_ten(
    world: World, client: TestClient, auth_headers: Headers
) -> None:
    st = world.student(world.a, world.cs)
    sc = world.score(st, 10, "Foundation", 10, role=world.r1)
    cat = world.db.execute(select(SkillCategory)).scalars().first()
    assert cat is not None
    for i in range(12):
        world.gap(sc, world.skill(world.a, cat, f"S{i:02d}"), GapStatus.GAP, GapPriority.LOW)
    assert len(get(client, auth_headers, world.tpo).json()["top_gaps"]) == 10


def test_audit_row(
    world: World, client: TestClient, auth_headers: Headers, db: Session
) -> None:
    get(client, auth_headers, world.tpo)
    get(client, auth_headers, world.tpo, department_id=world.cs.id)
    rows = db.execute(
        select(AuditLog).where(AuditLog.action == "DASHBOARD_PLACEMENT_READ")
    ).scalars().all()
    assert len(rows) == 2
    assert {r.user_id for r in rows} == {world.tpo.id}
    assert {r.college_id for r in rows} == {world.a.id}


def test_query_count_is_bounded(
    world: World, client: TestClient, auth_headers: Headers, db: Session
) -> None:
    def add_students(n: int) -> None:
        for i in range(n):
            st = world.student(world.a, world.cs if i % 2 else world.ec, complete=True)
            world.score(st, 50 + i, "Developing", 40)
            sc = world.score(st, 20, "Foundation", 10, role=world.r1)
            world.gap(sc, world.py, GapStatus.GAP, GapPriority.HIGH)
            world.attempt(world.assessment(world.a, AssessmentStatus.PUBLISHED), st,
                          AttemptStatus.SUBMITTED)

    def count() -> int:
        statements: list[str] = []

        def listener(*args: Any) -> None:
            statements.append(str(args[2]))

        engine = db.get_bind()
        event.listen(engine, "before_cursor_execute", listener)
        try:
            assert get(client, auth_headers, world.tpo).status_code == 200
        finally:
            event.remove(engine, "before_cursor_execute", listener)
        return len(statements)

    add_students(3)
    small = count()
    add_students(9)
    large = count()
    assert small == large
    assert large < 20
