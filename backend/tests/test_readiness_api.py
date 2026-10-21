"""Phase 3 API tests: rules, career roles, readiness compute/read, access, isolation, audit."""
import json
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    College,
    Department,
    FacultyAssignment,
    ReadinessScore,
    Skill,
    SkillCategory,
    SkillGap,
    Student,
    StudentSkill,
    User,
    UserRole,
)

Headers = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]
API = "/api/v1"


class Env:
    """College A (admin, faculty, tpo, hod, 2 students) and college B (admin, student)."""

    def __init__(
        self, client: TestClient, db: Session, h: Headers, make_user: MakeUser,
        a: College, b: College,
    ) -> None:
        self.client, self.db, self.h = client, db, h
        self.a, self.b = a, b
        self.admin = make_user(a, UserRole.ADMIN)
        self.faculty = make_user(a, UserRole.FACULTY)
        self.tpo = make_user(a, UserRole.TPO)
        self.hod = make_user(a, UserRole.HOD)
        self.super_admin = make_user(a, UserRole.SUPER_ADMIN)
        self.student = make_user(a, UserRole.STUDENT)
        self.student2 = make_user(a, UserRole.STUDENT, email="s2@a.example.com")
        self.admin_b = make_user(b, UserRole.ADMIN)
        self.tpo_b = make_user(b, UserRole.TPO)
        self.student_b = make_user(b, UserRole.STUDENT)
        self.cat1 = self.category(a, "Technical")
        self.cat2 = self.category(a, "Aptitude")
        self.py = self.skill(a, self.cat1, "Python")
        self.sql = self.skill(a, self.cat1, "SQL")
        self.logic = self.skill(a, self.cat2, "Logic")

    def req(self, method: str, path: str, user: User, **kw: Any) -> Any:
        return self.client.request(method, API + path, headers=self.h(user), **kw)

    def category(self, college: College, name: str) -> SkillCategory:
        obj = SkillCategory(college_id=college.id, name=name)
        self.db.add(obj)
        self.db.commit()
        return obj

    def skill(self, college: College, cat: SkillCategory, name: str) -> Skill:
        obj = Skill(college_id=college.id, category_id=cat.id, name=name)
        self.db.add(obj)
        self.db.commit()
        return obj

    def student_row(self, user: User, dept: Department | None = None) -> Student:
        row = Student(
            user_id=user.id, college_id=user.college_id,
            department_id=dept.id if dept else None,
        )
        self.db.add(row)
        self.db.commit()
        return row

    def give_score(self, student: Student, skill: Skill, score: float) -> None:
        self.db.add(
            StudentSkill(
                student_id=student.id, college_id=student.college_id, skill_id=skill.id,
                score=Decimal(str(score)), evidence_count=2,
            )
        )
        self.db.commit()

    def dept(self, college: College, code: str = "CS") -> Department:
        obj = Department(college_id=college.id, name=f"Dept {code}", code=code)
        self.db.add(obj)
        self.db.commit()
        return obj

    def rule_body(self, **over: Any) -> dict[str, Any]:
        body: dict[str, Any] = {
            "weights": {str(self.cat1.id): 60, str(self.cat2.id): 40},
            "level_thresholds": [
                {"level": "Foundation", "min_score": 0},
                {"level": "Developing", "min_score": 50},
                {"level": "Strong", "min_score": 80},
            ],
            "gap_thresholds": {"high_min_gap": 30, "medium_min_gap": 15},
        }
        body.update(over)
        return body

    def active_rule(self, **over: Any) -> dict[str, Any]:
        r = self.req("POST", "/admin/readiness-rules", self.admin, json=self.rule_body(**over))
        assert r.status_code == 201, r.text
        a = self.req("POST", f"/admin/readiness-rules/{r.json()['id']}/activate", self.admin)
        assert a.status_code == 200, a.text
        return dict(a.json())

    def role(self, name: str = "Data Analyst", **over: Any) -> int:
        r = self.req("POST", "/admin/career-roles", self.admin, json={"name": name, **over})
        assert r.status_code == 201, r.text
        return int(r.json()["id"])

    def role_skills(self, role_id: int) -> None:
        r = self.req(
            "PUT", f"/admin/career-roles/{role_id}/skills", self.admin,
            json=[
                {"skill_id": self.py.id, "required_level": 70, "weight": 3},
                {"skill_id": self.sql.id, "required_level": 60, "weight": 1},
                {"skill_id": self.logic.id, "required_level": 50, "weight": 1},
            ],
        )
        assert r.status_code == 200, r.text

    def actions(self) -> list[str]:
        return list(self.db.execute(select(AuditLog.action)).scalars())


def _env(
    client: TestClient, db: Session, auth_headers: Headers, make_user: MakeUser,
    college: College, other_college: College,
) -> Env:
    return Env(client, db, auth_headers, make_user, college, other_college)


import pytest  # noqa: E402


@pytest.fixture
def env(
    client: TestClient, db: Session, auth_headers: Headers, make_user: MakeUser,
    college: College, other_college: College,
) -> Env:
    """Scenario environment."""
    return _env(client, db, auth_headers, make_user, college, other_college)


# ---- rules -------------------------------------------------------------------------------
def test_compute_without_active_rule_is_409(env: Env) -> None:
    r = env.req("POST", "/readiness/compute", env.student, json={})
    assert r.status_code == 409
    assert r.json() == {"detail": "No active readiness rule configured"}
    # body-less POST behaves the same
    assert env.req("POST", "/readiness/compute", env.student).status_code == 409


def test_rule_versioning_and_single_active(env: Env) -> None:
    r1 = env.req("POST", "/admin/readiness-rules", env.admin, json=env.rule_body())
    assert r1.status_code == 201
    assert r1.json()["version"] == 1 and r1.json()["is_active"] is False
    assert r1.json()["created_by"] == env.admin.id
    r2 = env.req("POST", "/admin/readiness-rules", env.admin, json=env.rule_body())
    assert r2.json()["version"] == 2
    env.req("POST", f"/admin/readiness-rules/{r1.json()['id']}/activate", env.admin)
    env.req("POST", f"/admin/readiness-rules/{r2.json()['id']}/activate", env.admin)
    # activating again is idempotent
    env.req("POST", f"/admin/readiness-rules/{r2.json()['id']}/activate", env.admin)
    rules = env.req("GET", "/admin/readiness-rules", env.admin).json()
    assert [(x["version"], x["is_active"]) for x in rules] == [(2, True), (1, False)]
    one = env.req("GET", f"/admin/readiness-rules/{r1.json()['id']}", env.admin)
    assert one.status_code == 200 and one.json()["version"] == 1
    assert env.req("PUT", f"/admin/readiness-rules/{r1.json()['id']}", env.admin).status_code == 405
    assert {"READINESS_RULE_CREATE", "READINESS_RULE_ACTIVATE"} <= set(env.actions())


def test_rule_validation_422(env: Env) -> None:
    c1 = str(env.cat1.id)
    bad: list[dict[str, Any]] = [
        {"weights": {}},
        {"weights": {"abc": 1}},
        {"weights": {c1: 0}},
        {"weights": {c1: -2}},
        {"weights": {"99999": 1}},
        {"level_thresholds": []},
        {"level_thresholds": [{"level": "A", "min_score": 0}, {"level": "A", "min_score": 50}]},
        {"level_thresholds": [{"level": "A", "min_score": 101}]},
        {"level_thresholds": [{"level": "A", "min_score": -1}]},
        {"level_thresholds": [{"level": "  ", "min_score": 10}]},
        {"gap_thresholds": {"high_min_gap": 10, "medium_min_gap": 20}},
        {"gap_thresholds": {"high_min_gap": 10, "medium_min_gap": 0}},
        {"gap_thresholds": {"high_min_gap": 101, "medium_min_gap": 20}},
        {"gap_thresholds": {"high_min_gap": 20}},
    ]
    for over in bad:
        r = env.req("POST", "/admin/readiness-rules", env.admin, json=env.rule_body(**over))
        assert r.status_code == 422, over
        assert "detail" in r.json()
    assert env.req("GET", "/admin/readiness-rules", env.admin).json() == []


def test_rule_weights_cannot_use_other_college_category(env: Env) -> None:
    foreign = env.category(env.b, "Foreign")
    r = env.req(
        "POST", "/admin/readiness-rules", env.admin,
        json=env.rule_body(weights={str(foreign.id): 10}),
    )
    assert r.status_code == 422


def test_rules_are_admin_only_and_isolated(env: Env) -> None:
    rule = env.active_rule()
    for user in (env.student, env.faculty, env.tpo, env.hod, env.super_admin):
        assert env.req("GET", "/admin/readiness-rules", user).status_code == 403
        assert env.req("POST", "/admin/readiness-rules", user, json=env.rule_body()).status_code == 403
        assert env.req("POST", f"/admin/readiness-rules/{rule['id']}/activate", user).status_code == 403
    assert env.client.get(API + "/admin/readiness-rules").status_code == 401
    assert env.req("GET", "/admin/readiness-rules", env.admin_b).json() == []
    assert env.req("GET", f"/admin/readiness-rules/{rule['id']}", env.admin_b).status_code == 404
    assert (
        env.req("POST", f"/admin/readiness-rules/{rule['id']}/activate", env.admin_b).status_code
        == 404
    )
    assert env.req("GET", "/admin/readiness-rules/999", env.admin).status_code == 404


def test_one_active_rule_per_college(env: Env, db: Session) -> None:
    env.active_rule()
    # college B can have its own active rule
    cat_b = env.category(env.b, "TechB")
    body = {
        "weights": {str(cat_b.id): 1},
        "level_thresholds": [{"level": "X", "min_score": 0}],
        "gap_thresholds": {"high_min_gap": 20, "medium_min_gap": 10},
    }
    rb = env.req("POST", "/admin/readiness-rules", env.admin_b, json=body)
    assert rb.json()["version"] == 1
    env.req("POST", f"/admin/readiness-rules/{rb.json()['id']}/activate", env.admin_b)
    assert [r["is_active"] for r in env.req("GET", "/admin/readiness-rules", env.admin).json()] == [
        True
    ]


# ---- career roles ------------------------------------------------------------------------
def test_admin_career_role_crud_and_skills(env: Env) -> None:
    dept = env.dept(env.a)
    role_id = env.role(description="d", department_id=dept.id)
    assert env.req("POST", "/admin/career-roles", env.admin, json={"name": "Data Analyst"}).status_code == 409
    assert env.req("POST", "/admin/career-roles", env.admin, json={"name": "X", "department_id": 999}).status_code == 422
    foreign_dept = env.dept(env.b, "EE")
    assert env.req("POST", "/admin/career-roles", env.admin, json={"name": "Y", "department_id": foreign_dept.id}).status_code == 422
    env.role_skills(role_id)
    detail = env.req("GET", f"/admin/career-roles/{role_id}", env.admin).json()
    assert detail["department_id"] == dept.id
    assert [(s["skill_name"], s["required_level"], s["weight"]) for s in detail["skills"]] == [
        ("Logic", 50.0, 1.0), ("Python", 70.0, 3.0), ("SQL", 60.0, 1.0),
    ]
    # bulk replace
    env.req("PUT", f"/admin/career-roles/{role_id}/skills", env.admin,
            json=[{"skill_id": env.py.id, "required_level": 10, "weight": 1}])
    assert len(env.req("GET", f"/admin/career-roles/{role_id}", env.admin).json()["skills"]) == 1
    env.req("PUT", f"/admin/career-roles/{role_id}/skills", env.admin, json=[])
    assert env.req("GET", f"/admin/career-roles/{role_id}", env.admin).json()["skills"] == []
    # skills validation
    path = f"/admin/career-roles/{role_id}/skills"
    dup = [{"skill_id": env.py.id, "required_level": 1, "weight": 1}] * 2
    assert env.req("PUT", path, env.admin, json=dup).status_code == 422
    assert env.req("PUT", path, env.admin, json=[{"skill_id": 9999, "required_level": 1, "weight": 1}]).status_code == 422
    foreign_skill = env.skill(env.b, env.category(env.b, "T"), "Foreign")
    assert env.req("PUT", path, env.admin, json=[{"skill_id": foreign_skill.id, "required_level": 1, "weight": 1}]).status_code == 422
    assert env.req("PUT", path, env.admin, json=[{"skill_id": env.py.id, "required_level": 101, "weight": 1}]).status_code == 422
    assert env.req("PUT", path, env.admin, json=[{"skill_id": env.py.id, "required_level": 1, "weight": 0}]).status_code == 422
    # update
    up = env.req("PUT", f"/admin/career-roles/{role_id}", env.admin,
                 json={"name": "Renamed", "is_active": False, "department_id": None, "description": None})
    assert up.status_code == 200
    assert up.json()["name"] == "Renamed" and up.json()["is_active"] is False
    assert up.json()["department_id"] is None
    other = env.role("Other")
    assert env.req("PUT", f"/admin/career-roles/{other}", env.admin, json={"name": "Renamed"}).status_code == 409
    assert env.req("PUT", f"/admin/career-roles/{other}", env.admin, json={"department_id": 999}).status_code == 422
    listed = env.req("GET", "/admin/career-roles", env.admin).json()
    assert {r["name"] for r in listed} == {"Renamed", "Other"}  # includes inactive
    assert {"CAREER_ROLE_CREATE", "CAREER_ROLE_UPDATE", "CAREER_ROLE_SKILLS_UPDATE"} <= set(env.actions())


def test_admin_career_role_guards_and_isolation(env: Env) -> None:
    role_id = env.role()
    for user in (env.student, env.faculty, env.tpo, env.hod, env.super_admin):
        assert env.req("GET", "/admin/career-roles", user).status_code == 403
        assert env.req("POST", "/admin/career-roles", user, json={"name": "Z"}).status_code == 403
        assert env.req("PUT", f"/admin/career-roles/{role_id}", user, json={"name": "Z"}).status_code == 403
        assert env.req("PUT", f"/admin/career-roles/{role_id}/skills", user, json=[]).status_code == 403
        assert env.req("GET", f"/admin/career-roles/{role_id}", user).status_code == 403
    assert env.req("GET", "/admin/career-roles", env.admin_b).json() == []
    assert env.req("GET", f"/admin/career-roles/{role_id}", env.admin_b).status_code == 404
    assert env.req("PUT", f"/admin/career-roles/{role_id}", env.admin_b, json={"name": "Z"}).status_code == 404
    assert env.req("PUT", f"/admin/career-roles/{role_id}/skills", env.admin_b, json=[]).status_code == 404
    # same name allowed in another college
    assert env.req("POST", "/admin/career-roles", env.admin_b, json={"name": "Data Analyst"}).status_code == 201


def test_student_role_visibility(env: Env) -> None:
    cs, ece = env.dept(env.a, "CS"), env.dept(env.a, "EC")
    env.student_row(env.student, cs)
    env.student_row(env.student2, ece)
    common = env.role("Common")
    cs_role = env.role("CS Role", department_id=cs.id)
    ec_role = env.role("EC Role", department_id=ece.id)
    inactive = env.role("Old", is_active=False)
    env.role_skills(common)
    seen = {r["name"] for r in env.req("GET", "/career-roles", env.student).json()}
    assert seen == {"Common", "CS Role"}
    seen2 = {r["name"] for r in env.req("GET", "/career-roles", env.student2).json()}
    assert seen2 == {"Common", "EC Role"}
    detail = env.req("GET", f"/career-roles/{common}", env.student).json()
    assert len(detail["skills"]) == 3 and detail["skills"][0]["skill_name"] == "Logic"
    assert env.req("GET", f"/career-roles/{cs_role}", env.student).status_code == 200
    for rid in (ec_role, inactive, 9999):
        assert env.req("GET", f"/career-roles/{rid}", env.student).status_code == 404
    # other college and non-students
    assert env.req("GET", f"/career-roles/{common}", env.student_b).status_code == 404
    assert env.req("GET", "/career-roles", env.student_b).json() == []
    assert env.req("GET", "/career-roles", env.faculty).status_code == 403


def test_student_without_department_sees_only_common_roles(env: Env) -> None:
    cs = env.dept(env.a)
    common = env.role("Common")
    env.role("CS Role", department_id=cs.id)
    assert [r["id"] for r in env.req("GET", "/career-roles", env.student).json()] == [common]


# ---- compute / read ----------------------------------------------------------------------
def test_general_compute_persists_with_rule_and_evidence(env: Env) -> None:
    rule = env.active_rule()
    st = env.student_row(env.student)
    env.give_score(st, env.py, 80)
    env.give_score(st, env.sql, 60)
    r = env.req("POST", "/readiness/compute", env.student, json={})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["overall"] == 70.0  # only Technical has evidence, renormalised
    assert body["coverage"] == 60.0
    assert body["level"] == "Developing"
    assert body["role_id"] is None and body["role_name"] is None and body["gaps"] == []
    assert (body["rule_id"], body["rule_version"]) == (rule["id"], 1)
    assert body["student_id"] == st.id
    cats = {c["category_name"]: c for c in body["category_scores"]}
    assert cats["Technical"]["score"] == 70.0 and cats["Technical"]["weight"] == 60.0
    assert cats["Technical"]["evidence_count"] == 4
    assert cats["Aptitude"]["score"] is None
    assert {e["skill_name"] for e in body["evidence"]} == {"Python", "SQL"}
    assert set(body["evidence"][0]) == {
        "skill_id", "skill_name", "category_name", "score", "evidence_count", "last_result_id"
    }
    mine = env.req("GET", "/readiness/me", env.student)
    assert mine.status_code == 200 and mine.json()["id"] == body["id"]
    stored = env.db.get(ReadinessScore, body["id"])
    assert stored is not None and stored.rule_version == 1 and len(stored.evidence) == 2
    assert "READINESS_COMPUTE" in env.actions()


def test_zero_coverage_has_null_overall_and_level(env: Env) -> None:
    env.active_rule()
    body = env.req("POST", "/readiness/compute", env.student, json={}).json()
    assert body["overall"] is None and body["level"] is None and body["coverage"] == 0.0
    assert all(c["score"] is None for c in body["category_scores"])


def test_level_null_when_no_threshold_matches(env: Env) -> None:
    env.active_rule(level_thresholds=[{"level": "Strong", "min_score": 90}])
    st = env.student_row(env.student)
    env.give_score(st, env.py, 50)
    body = env.req("POST", "/readiness/compute", env.student, json={}).json()
    assert body["overall"] == 50.0 and body["level"] is None


def test_role_compute_gaps_and_history(env: Env) -> None:
    env.active_rule()
    role_id = env.role()
    env.role_skills(role_id)
    st = env.student_row(env.student)
    env.give_score(st, env.py, 40)
    env.give_score(st, env.sql, 65)
    r = env.req("POST", "/readiness/compute", env.student, json={"role_id": role_id})
    assert r.status_code == 201, r.text
    body = r.json()
    # (3*40 + 1*65) / 4 = 46.25 ; coverage 4/5 = 80
    assert body["overall"] == 46.25 and body["coverage"] == 80.0
    assert body["level"] == "Foundation"
    assert body["role_id"] == role_id and body["role_name"] == "Data Analyst"
    gaps = {g["skill_name"]: g for g in body["gaps"]}
    assert (gaps["Python"]["gap"], gaps["Python"]["status"], gaps["Python"]["priority"]) == (
        30.0, "GAP", "HIGH")
    assert gaps["Python"]["recommended_action"] == (
        "Improve Python: close a gap of 30 points (current 40, required 70)")
    assert (gaps["SQL"]["gap"], gaps["SQL"]["status"], gaps["SQL"]["priority"]) == (
        0.0, "READY", "NONE")
    assert gaps["SQL"]["recommended_action"] == "No action needed"
    assert (gaps["Logic"]["current"], gaps["Logic"]["gap"], gaps["Logic"]["status"]) == (
        None, None, "NO_EVIDENCE")
    assert gaps["Logic"]["priority"] == "UNASSESSED"
    assert gaps["Logic"]["recommended_action"] == "Complete an assessment that covers Logic"
    assert set(gaps["Python"]) == {
        "skill_id", "skill_name", "current", "required", "gap", "status", "priority",
        "recommended_action"}
    assert env.db.execute(select(SkillGap)).scalars().all().__len__() == 3

    mine = env.req("GET", "/readiness/me", env.student, params={"role_id": role_id}).json()
    assert mine["id"] == body["id"] and len(mine["gaps"]) == 3
    g = env.req("GET", "/readiness/gaps", env.student, params={"role_id": role_id})
    assert g.status_code == 200 and len(g.json()) == 3

    # recompute after improvement: newest first in history, gaps omitted there
    st_skill = env.db.execute(select(StudentSkill).where(StudentSkill.skill_id == env.py.id)).scalar_one()
    st_skill.score = Decimal("75")
    env.db.commit()
    second = env.req("POST", "/readiness/compute", env.student, json={"role_id": role_id}).json()
    assert second["id"] != body["id"]
    hist = env.req("GET", "/readiness/me/history", env.student, params={"role_id": role_id}).json()
    assert [h["id"] for h in hist] == [second["id"], body["id"]]
    assert all(h["gaps"] == [] for h in hist)
    # general history is separate from role history
    assert env.req("GET", "/readiness/me/history", env.student).json() == []
    assert env.req("GET", "/readiness/me", env.student).status_code == 404
    latest_gaps = env.req("GET", "/readiness/gaps", env.student, params={"role_id": role_id}).json()
    assert {x["skill_name"]: x["status"] for x in latest_gaps}["Python"] == "READY"


def test_reads_404_when_never_computed_and_gaps_requires_role_id(env: Env) -> None:
    env.active_rule()
    role_id = env.role()
    assert env.req("GET", "/readiness/me", env.student).status_code == 404
    assert env.req("GET", "/readiness/me", env.student, params={"role_id": role_id}).status_code == 404
    assert env.req("GET", "/readiness/gaps", env.student, params={"role_id": role_id}).status_code == 404
    assert env.req("GET", "/readiness/gaps", env.student).status_code == 422
    assert env.req("GET", "/readiness/me/history", env.student).json() == []


def test_old_scores_keep_their_rule_version(env: Env) -> None:
    first = env.active_rule()
    st = env.student_row(env.student)
    env.give_score(st, env.py, 80)
    old = env.req("POST", "/readiness/compute", env.student, json={}).json()
    new_rule = env.active_rule(level_thresholds=[{"level": "Elite", "min_score": 10}])
    assert new_rule["version"] == 2
    after = env.req("POST", "/readiness/compute", env.student, json={}).json()
    assert after["rule_version"] == 2 and after["rule_id"] == new_rule["id"]
    assert after["level"] == "Elite"
    hist = env.req("GET", "/readiness/me/history", env.student).json()
    by_id = {h["id"]: h for h in hist}
    assert by_id[old["id"]]["rule_version"] == 1 and by_id[old["id"]]["rule_id"] == first["id"]
    assert by_id[old["id"]]["level"] == "Strong"


def test_compute_role_visibility_rules(env: Env) -> None:
    env.active_rule()
    cs, ece = env.dept(env.a, "CS"), env.dept(env.a, "EC")
    env.student_row(env.student, cs)
    ok = env.role("OK", department_id=cs.id)
    wrong_dept = env.role("Wrong", department_id=ece.id)
    inactive = env.role("Inactive", is_active=False)
    role_b = int(env.req("POST", "/admin/career-roles", env.admin_b, json={"name": "B"}).json()["id"])
    assert env.req("POST", "/readiness/compute", env.student, json={"role_id": ok}).status_code == 201
    for rid in (wrong_dept, inactive, role_b, 9999):
        assert env.req("POST", "/readiness/compute", env.student, json={"role_id": rid}).status_code == 404


def test_compute_requires_student_role(env: Env) -> None:
    env.active_rule()
    for user in (env.faculty, env.tpo, env.hod, env.admin, env.super_admin):
        assert env.req("POST", "/readiness/compute", user, json={}).status_code == 403
        assert env.req("GET", "/readiness/me", user).status_code == 403
        assert env.req("GET", "/readiness/me/history", user).status_code == 403
        assert env.req("GET", "/readiness/gaps", user, params={"role_id": 1}).status_code == 403
    assert env.client.post(API + "/readiness/compute", json={}).status_code == 401


def test_student_skills_of_other_college_never_leak(env: Env) -> None:
    env.active_rule()
    # college B student with a high score under their own college
    cat_b = env.category(env.b, "TechB")
    skill_b = env.skill(env.b, cat_b, "PythonB")
    st_b = env.student_row(env.student_b)
    env.give_score(st_b, skill_b, 99)
    # college A rule is active, B has none -> B student gets 409, A student sees nothing of B
    assert env.req("POST", "/readiness/compute", env.student_b, json={}).status_code == 409
    a = env.req("POST", "/readiness/compute", env.student, json={}).json()
    assert a["overall"] is None and a["evidence"] == []


# ---- staff reads -------------------------------------------------------------------------
def _computed(env: Env) -> tuple[Student, dict[str, Any]]:
    env.active_rule()
    st = env.student_row(env.student)
    env.give_score(st, env.py, 80)
    return st, env.req("POST", "/readiness/compute", env.student, json={}).json()


def test_staff_access_rules(env: Env) -> None:
    st, body = _computed(env)
    path = f"/readiness/{st.id}"
    # faculty: only when assigned
    assert env.req("GET", path, env.faculty).status_code == 404
    env.db.add(FacultyAssignment(college_id=env.a.id, faculty_user_id=env.faculty.id, student_id=st.id))
    env.db.commit()
    ok = env.req("GET", path, env.faculty)
    assert ok.status_code == 200 and ok.json()["id"] == body["id"]
    assert env.req("GET", path, env.tpo).status_code == 200
    assert env.req("GET", path, env.admin).status_code == 200
    assert env.req("GET", path, env.hod).status_code == 403
    assert env.req("GET", path, env.super_admin).status_code == 403
    # other college staff get 404
    assert env.req("GET", path, env.tpo_b).status_code == 404
    assert env.req("GET", path, env.admin_b).status_code == 404
    # students: own only
    assert env.req("GET", path, env.student).status_code == 200
    assert env.req("GET", path, env.student2).status_code == 404
    assert env.client.get(API + path).status_code == 401
    # staff reads are audited (3 staff successes), a student self-read is not
    reads = env.db.execute(select(AuditLog).where(AuditLog.action == "READINESS_READ")).scalars().all()
    assert len(reads) == 3
    assert {r.user_id for r in reads} == {env.faculty.id, env.tpo.id, env.admin.id}


def test_staff_read_not_computed_and_role_param(env: Env) -> None:
    env.active_rule()
    st = env.student_row(env.student)
    assert env.req("GET", f"/readiness/{st.id}", env.tpo).status_code == 404
    role_id = env.role()
    env.role_skills(role_id)
    env.give_score(st, env.py, 40)
    env.req("POST", "/readiness/compute", env.student, json={"role_id": role_id})
    r = env.req("GET", f"/readiness/{st.id}", env.tpo, params={"role_id": role_id})
    assert r.status_code == 200 and len(r.json()["gaps"]) == 3
    assert env.req("GET", f"/readiness/{st.id}", env.tpo).status_code == 404  # no general score
    assert env.req("GET", "/readiness/99999", env.tpo).status_code == 404


# ---- language / secrets ------------------------------------------------------------------
def test_no_probability_language_in_responses(env: Env) -> None:
    rule = env.active_rule()
    role_id = env.role()
    env.role_skills(role_id)
    st = env.student_row(env.student)
    env.give_score(st, env.py, 40)
    texts: list[str] = [json.dumps(rule)]
    texts.append(env.req("POST", "/readiness/compute", env.student, json={}).text)
    texts.append(env.req("POST", "/readiness/compute", env.student, json={"role_id": role_id}).text)
    texts.append(env.req("GET", "/readiness/me", env.student).text)
    texts.append(env.req("GET", "/readiness/me/history", env.student).text)
    texts.append(env.req("GET", "/readiness/gaps", env.student, params={"role_id": role_id}).text)
    texts.append(env.req("GET", "/career-roles", env.student).text)
    texts.append(env.req("GET", f"/readiness/{st.id}", env.tpo).text)
    texts.append(env.req("GET", "/admin/readiness-rules", env.admin).text)
    for text in texts:
        low = text.lower()
        assert "probab" not in low and "chance" not in low and "likelihood" not in low
