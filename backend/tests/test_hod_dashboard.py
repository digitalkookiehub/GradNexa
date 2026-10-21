"""HOD dashboard tests (also hosts the shared World dataset builder for phase 8.3 tests)."""
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
    Assessment,
    AssessmentAttempt,
    AssessmentResult,
    AssessmentStatus,
    AssessmentType,
    AttemptStatus,
    AuditLog,
    CareerRole,
    College,
    Company,
    Department,
    EligibilityRule,
    GapPriority,
    GapStatus,
    HodAssignment,
    JobDescription,
    JobStatus,
    ReadinessRule,
    ReadinessScore,
    Skill,
    SkillCategory,
    SkillGap,
    Student,
    StudentCareerGoal,
    StudentSkill,
    User,
    UserRole,
)

Headers = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]
URL = "/api/v1/dashboard/hod"
T0 = datetime(2026, 1, 1, tzinfo=UTC)


class World:
    """Hand-built dataset: college A (3 departments) plus helpers for college B."""

    def __init__(self, db: Session, make_user: MakeUser, a: College, b: College) -> None:
        self.db, self.make_user, self.a, self.b = db, make_user, a, b
        self.admin = make_user(a, UserRole.ADMIN)
        self.tpo = make_user(a, UserRole.TPO)
        self.hod = make_user(a, UserRole.HOD)
        self.faculty = make_user(a, UserRole.FACULTY, email="fac1@a.test")
        self.faculty2 = make_user(a, UserRole.FACULTY, email="fac2@a.test")
        self.admin_b = make_user(b, UserRole.ADMIN)
        self.tpo_b = make_user(b, UserRole.TPO)
        self.hod_b = make_user(b, UserRole.HOD)
        self.cs = self.dept(a, "CS", "Computer Science")
        self.ec = self.dept(a, "EC", "Electronics")
        self.me = self.dept(a, "ME", "Mechanical")
        cat = SkillCategory(college_id=a.id, name="Tech")
        db.add(cat)
        db.commit()
        self.cat = cat
        self.py = self.skill(a, "Python")
        self.sql = self.skill(a, "SQL")
        self.logic = self.skill(a, "Logic")
        self.r1 = self.role(a, "Role One")
        self.r2 = self.role(a, "Role Two")
        self.rule1 = self.rule(a, 1, False)
        self.rule2 = self.rule(a, 2, True)
        self.n = 0

    # ---- builders ----
    def assign_hod(self, user: User, *depts: Department) -> None:
        for d in depts:
            self.db.add(
                HodAssignment(college_id=user.college_id, hod_user_id=user.id, department_id=d.id)
            )
        self.db.commit()

    def dept(self, college: College, code: str, name: str) -> Department:
        obj = Department(college_id=college.id, name=name, code=code)
        self.db.add(obj)
        self.db.commit()
        return obj

    def skill(self, college: College, name: str) -> Skill:
        cat = self.cat
        if cat.college_id != college.id:
            cat = SkillCategory(college_id=college.id, name=f"Cat {name}")
            self.db.add(cat)
            self.db.commit()
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
        name: str | None = None, grad: int | None = None,
    ) -> Student:
        self.n += 1
        user = self.make_user(college, UserRole.STUDENT, email=f"stu{self.n}@x{college.id}.test")
        user.full_name = name or f"Pupil {self.n:02d}"
        row = Student(
            user_id=user.id, college_id=college.id,
            department_id=dept.id if dept else None,
            roll_number=f"R{self.n}" if complete else None,
            graduation_year=2027 if complete else grad,
        )
        self.db.add(row)
        self.db.commit()
        return row

    def score(
        self, st: Student, overall: float | None, level: str | None, cov: float,
        version: int = 2, role: CareerRole | None = None, age: float = 0,
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

    def gap(self, sc: ReadinessScore, skill: Skill, status: GapStatus, prio: GapPriority) -> None:
        assert sc.role_id is not None
        self.db.add(
            SkillGap(
                student_id=sc.student_id, college_id=sc.college_id, role_id=sc.role_id,
                skill_id=skill.id, readiness_score_id=sc.id, required=Decimal("70"),
                status=status, priority=prio, recommended_action="x",
            )
        )
        self.db.commit()

    def skill_score(self, st: Student, skill: Skill, score: float) -> None:
        self.db.add(
            StudentSkill(
                student_id=st.id, college_id=st.college_id, skill_id=skill.id,
                score=Decimal(str(score)), evidence_count=1,
            )
        )
        self.db.commit()

    def goal(self, st: Student, role: CareerRole, priority: int = 1) -> None:
        self.db.add(
            StudentCareerGoal(
                student_id=st.id, college_id=st.college_id, career_role_id=role.id,
                priority=priority,
            )
        )
        self.db.commit()

    def assessment(
        self, college: College, status: AssessmentStatus = AssessmentStatus.PUBLISHED,
        title: str = "Quiz",
    ) -> Assessment:
        self.n += 1
        obj = Assessment(
            college_id=college.id, series_key=f"s{self.n}", title=title,
            type=AssessmentType.TECHNICAL, status=status, created_by=self.admin.id,
        )
        self.db.add(obj)
        self.db.commit()
        return obj

    def attempt(
        self, a: Assessment, st: Student, status: AttemptStatus = AttemptStatus.SUBMITTED,
        no: int = 1, pct: float | None = None, when: datetime | None = None,
    ) -> AssessmentAttempt:
        att = AssessmentAttempt(
            assessment_id=a.id, student_id=st.id, college_id=st.college_id,
            attempt_no=no, status=status,
            submitted_at=when if status == AttemptStatus.SUBMITTED else None,
        )
        self.db.add(att)
        self.db.commit()
        if pct is not None:
            self.db.add(
                AssessmentResult(
                    attempt_id=att.id, college_id=st.college_id, student_id=st.id,
                    assessment_id=a.id, assessment_version=1, total_score=Decimal(pct),
                    max_score=Decimal(100), percentage=Decimal(str(pct)),
                    computed_at=when or T0,
                )
            )
            self.db.commit()
        return att

    def job(
        self, college: College, title: str, status: JobStatus = JobStatus.OPEN,
        deadline: date | None = None, company: Company | None = None,
        rule: dict[str, Any] | None = None,
    ) -> JobDescription:
        if company is None:
            company = Company(college_id=college.id, name=f"Co {title}")
            self.db.add(company)
            self.db.commit()
        obj = JobDescription(
            college_id=college.id, company_id=company.id, title=title, body="b",
            status=status, application_deadline=deadline, created_by=self.admin.id,
        )
        self.db.add(obj)
        self.db.commit()
        if rule is not None:
            self.db.add(EligibilityRule(job_id=obj.id, college_id=college.id, **rule))
            self.db.commit()
        return obj

    def populate(self) -> dict[str, Student]:
        """Departments cs/ec (assigned to the HOD in tests) and me (never assigned)."""
        s1 = self.student(self.a, self.cs, complete=True)
        s2 = self.student(self.a, self.cs, grad=None)
        s3 = self.student(self.a, self.ec)
        s4 = self.student(self.a, self.ec)
        s5 = self.student(self.a, self.ec)  # nothing at all
        s6 = self.student(self.a, self.me)  # unassigned department
        self.score(s1, 40, "Foundation", 30, version=1, age=0)
        self.score(s1, 85, "Strong", 100, age=5)
        self.score(s2, 60, "Developing", 50)
        self.score(s3, 30, "Foundation", 20, version=1)
        self.score(s4, None, None, 0)
        self.score(s6, 99, "Strong", 99)
        self.score(s1, 10, "Foundation", 10, role=self.r1, age=1)
        old = self.score(s1, 10, "Foundation", 10, role=self.r1, age=2)
        self.gap(old, self.logic, GapStatus.GAP, GapPriority.HIGH)  # superseded gap set
        new = self.score(s1, 20, "Foundation", 10, role=self.r1, age=6)
        self.gap(new, self.py, GapStatus.GAP, GapPriority.HIGH)
        self.gap(new, self.sql, GapStatus.GAP, GapPriority.LOW)
        s2r = self.score(s2, 30, "Foundation", 10, role=self.r1)
        self.gap(s2r, self.py, GapStatus.GAP, GapPriority.HIGH)
        self.gap(s2r, self.sql, GapStatus.READY, GapPriority.NONE)
        s3r = self.score(s3, 30, "Foundation", 10, role=self.r1)
        self.gap(s3r, self.sql, GapStatus.GAP, GapPriority.HIGH)
        self.gap(s3r, self.logic, GapStatus.NO_EVIDENCE, GapPriority.UNASSESSED)
        s6r = self.score(s6, 5, "Foundation", 5, role=self.r1)
        self.gap(s6r, self.py, GapStatus.GAP, GapPriority.HIGH)
        self.skill_score(s1, self.py, 80)
        self.skill_score(s2, self.py, 60)
        self.skill_score(s3, self.sql, 50)
        self.skill_score(s6, self.py, 100)
        self.goal(s1, self.r1)
        self.goal(s1, self.r2, 2)
        self.goal(s2, self.r1)
        self.goal(s3, self.r2)
        self.goal(s6, self.r1)
        q = self.assessment(self.a)
        jan = T0 + timedelta(days=3)
        feb = T0 + timedelta(days=40)
        self.attempt(q, s1, no=1, pct=80, when=jan)
        self.attempt(q, s2, no=1, pct=60, when=jan)
        self.attempt(q, s3, no=1, pct=50, when=feb)
        self.attempt(q, s6, no=1, pct=10, when=feb)
        self.attempt(q, s2, AttemptStatus.IN_PROGRESS, no=2)
        return {"s1": s1, "s2": s2, "s3": s3, "s4": s4, "s5": s5, "s6": s6}


@pytest.fixture
def world(
    db: Session, college: College, other_college: College, make_user: MakeUser
) -> World:
    return World(db, make_user, college, other_college)


def get(client: TestClient, h: Headers, user: User, **params: Any) -> Any:
    return client.get(URL, headers=h(user), params=params)


def count_statements(db: Session, fn: Callable[[], Any]) -> int:
    """Number of SQL statements executed while running fn."""
    statements: list[str] = []

    def listener(*args: Any) -> None:
        statements.append(str(args[2]))

    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", listener)
    try:
        fn()
    finally:
        event.remove(engine, "before_cursor_execute", listener)
    assert not any("select *" in s.lower() for s in statements)
    return len(statements)


def test_combined_scope_aggregates(
    world: World, client: TestClient, auth_headers: Headers
) -> None:
    world.populate()
    world.assign_hod(world.hod, world.cs, world.ec)
    r = get(client, auth_headers, world.hod)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["scope"] == {
        "department_ids": sorted([world.cs.id, world.ec.id]),
        "department_names": ["Computer Science", "Electronics"],
    }
    assert b["rule"] == {"id": world.rule2.id, "version": 2}
    assert b["rule_versions_in_use"] == [1, 2]
    assert b["totals"] == {
        "students": 5, "profile_complete": 1, "with_readiness_score": 4,
        "with_assessment_submitted": 3,
    }
    assert b["level_distribution"] == [
        {"level": "Strong", "count": 1},
        {"level": "Developing", "count": 1},
        {"level": "Foundation", "count": 1},
        {"level": None, "count": 2},
    ]
    assert b["skill_heatmap"] == [
        {"skill_id": world.py.id, "skill_name": "Python", "category_name": "Tech",
         "students_assessed": 2, "average_score": 70.0},
        {"skill_id": world.sql.id, "skill_name": "SQL", "category_name": "Tech",
         "students_assessed": 1, "average_score": 50.0},
    ]
    assert b["career_role_distribution"] == [
        {"role_id": world.r1.id, "role_name": "Role One", "students": 2},
        {"role_id": world.r2.id, "role_name": "Role Two", "students": 2},
    ]
    assert b["assessment_trends"] == [
        {"month": "2026-01", "submitted_attempts": 2, "average_percentage": 70.0},
        {"month": "2026-02", "submitted_attempts": 1, "average_percentage": 50.0},
    ]
    # Only the latest stored gap set per student+role counts (s1's superseded Logic gap is out).
    assert b["training_priorities"] == [
        {"skill_id": world.py.id, "skill_name": "Python", "students_affected": 2,
         "high_priority_students": 2},
        {"skill_id": world.sql.id, "skill_name": "SQL", "students_affected": 2,
         "high_priority_students": 1},
    ]
    assert isinstance(b["skill_heatmap"][0]["average_score"], float)


def test_single_department_scope(
    world: World, client: TestClient, auth_headers: Headers
) -> None:
    world.populate()
    world.assign_hod(world.hod, world.cs, world.ec)
    b = get(client, auth_headers, world.hod, department_id=world.cs.id).json()
    assert b["scope"] == {
        "department_ids": [world.cs.id], "department_names": ["Computer Science"],
    }
    assert b["totals"]["students"] == 2
    assert b["rule_versions_in_use"] == [2]
    assert b["level_distribution"] == [
        {"level": "Strong", "count": 1}, {"level": "Developing", "count": 1},
    ]
    assert [c["students"] for c in b["career_role_distribution"]] == [2, 1]
    assert b["training_priorities"][1] == {
        "skill_id": world.sql.id, "skill_name": "SQL", "students_affected": 1,
        "high_priority_students": 0,
    }


def test_unassigned_department_is_forbidden(
    world: World, client: TestClient, auth_headers: Headers
) -> None:
    world.populate()
    world.assign_hod(world.hod, world.cs)
    r = get(client, auth_headers, world.hod, department_id=world.me.id)
    assert r.status_code == 403
    assert "detail" in r.json()
    # a department of another college is just as forbidden, never a leak
    foreign = world.dept(world.b, "ZZ", "Foreign")
    assert get(client, auth_headers, world.hod, department_id=foreign.id).status_code == 403
    assert get(client, auth_headers, world.hod, department_id=99999).status_code == 403
    # unassigned department data never shows in the default scope
    assert get(client, auth_headers, world.hod).json()["totals"]["students"] == 2


def test_no_assignment_forbidden(
    world: World, client: TestClient, auth_headers: Headers
) -> None:
    r = get(client, auth_headers, world.hod)
    assert r.status_code == 403
    assert r.json() == {"detail": "No department assigned"}
    assert get(client, auth_headers, world.hod, department_id=world.cs.id).status_code == 403


@pytest.mark.parametrize(
    "role",
    [UserRole.TPO, UserRole.ADMIN, UserRole.FACULTY, UserRole.STUDENT, UserRole.SUPER_ADMIN],
)
def test_role_guards(
    world: World, client: TestClient, auth_headers: Headers, make_user: MakeUser,
    role: UserRole,
) -> None:
    user = make_user(world.a, role, email=f"g-{role.value}@x.test")
    assert get(client, auth_headers, user).status_code == 403
    assert client.get(URL).status_code == 401


def test_aggregates_only(world: World, client: TestClient, auth_headers: Headers) -> None:
    world.populate()
    world.assign_hod(world.hod, world.cs, world.ec)
    raw = get(client, auth_headers, world.hod).text
    assert "@" not in raw
    assert "pupil" not in raw.lower()
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
    # HOD of college B assigned to a college B department sees none of college A.
    db_b = world.dept(world.b, "BB", "B Dept")
    world.assign_hod(world.hod_b, db_b)
    sb = world.student(world.b, db_b, complete=True)
    world.score(sb, 70, "Developing", 70)
    b = get(client, auth_headers, world.hod_b).json()
    assert b["totals"] == {
        "students": 1, "profile_complete": 1, "with_readiness_score": 1,
        "with_assessment_submitted": 0,
    }
    assert b["skill_heatmap"] == [] and b["training_priorities"] == []
    assert b["rule"] is None
    # An assignment row pointing at college A's department from college B's HOD grants nothing.
    world.assign_hod(world.hod_b, world.cs)
    b2 = get(client, auth_headers, world.hod_b).json()
    assert b2["scope"]["department_names"] == ["B Dept"]
    assert b2["totals"]["students"] == 1


def test_empty_department(world: World, client: TestClient, auth_headers: Headers) -> None:
    world.assign_hod(world.hod, world.me)
    b = get(client, auth_headers, world.hod).json()
    assert b["totals"] == {
        "students": 0, "profile_complete": 0, "with_readiness_score": 0,
        "with_assessment_submitted": 0,
    }
    assert b["level_distribution"] == []
    assert b["assessment_trends"] == []


def test_trends_limited_to_twelve_months_ascending(
    world: World, client: TestClient, auth_headers: Headers
) -> None:
    world.assign_hod(world.hod, world.cs)
    st = world.student(world.a, world.cs)
    q = world.assessment(world.a)
    for i in range(14):
        world.attempt(q, st, no=i + 1, pct=50 + i, when=datetime(2025, 1 + i % 12, 5, tzinfo=UTC)
                      + timedelta(days=366 * (i // 12)))
    months = [t["month"] for t in get(client, auth_headers, world.hod).json()["assessment_trends"]]
    assert len(months) == 12
    assert months == sorted(months)
    assert months[-1] == "2026-02"


def test_audit_row(
    world: World, client: TestClient, auth_headers: Headers, db: Session
) -> None:
    world.assign_hod(world.hod, world.cs)
    get(client, auth_headers, world.hod)
    get(client, auth_headers, world.hod, department_id=world.cs.id)
    rows = db.execute(
        select(AuditLog).where(AuditLog.action == "DASHBOARD_HOD_READ")
    ).scalars().all()
    assert len(rows) == 2
    assert {r.user_id for r in rows} == {world.hod.id}
    assert {r.college_id for r in rows} == {world.a.id}


def test_statement_count_is_bounded(
    world: World, client: TestClient, auth_headers: Headers, db: Session
) -> None:
    world.assign_hod(world.hod, world.cs, world.ec)

    def add(n: int) -> None:
        for i in range(n):
            st = world.student(world.a, world.cs if i % 2 else world.ec, complete=True)
            world.score(st, 50 + i, "Developing", 40)
            sc = world.score(st, 20, "Foundation", 10, role=world.r1)
            world.gap(sc, world.py, GapStatus.GAP, GapPriority.HIGH)
            world.skill_score(st, world.sql, 40 + i)
            world.goal(st, world.r1)
            world.attempt(world.assessment(world.a), st, pct=70, when=T0 + timedelta(days=i * 20))

    def run() -> None:
        assert get(client, auth_headers, world.hod).status_code == 200

    add(3)
    small = count_statements(db, run)
    add(9)
    large = count_statements(db, run)
    assert small == large
    assert large < 25
