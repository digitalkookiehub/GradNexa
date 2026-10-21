"""Phase 4 API tests: goals, resources, plans, reassessment, isolation, audit."""
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, College, LearningPlan, LearningPlanItem, Skill, User, UserRole
from tests.test_readiness_api import Env

Headers = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


@pytest.fixture
def env(
    client: TestClient, db: Session, auth_headers: Headers, make_user: MakeUser,
    college: College, other_college: College,
) -> Env:
    """College A/B scenario with an active rule, a role with 3 skills and evidence."""
    e = Env(client, db, auth_headers, make_user, college, other_college)
    e.active_rule()
    return e


class Scenario:
    """Student with Python=40 (HIGH gap), SQL=50 (LOW gap), Logic without evidence."""

    def __init__(self, env: Env) -> None:
        self.env = env
        self.role = env.role()
        env.role_skills(self.role)
        row = env.student_row(env.student)
        env.give_score(row, env.py, 40)
        env.give_score(row, env.sql, 50)
        self.row = row

    def compute(self) -> dict[str, Any]:
        r = self.env.req("POST", "/readiness/compute", self.env.student, json={"role_id": self.role})
        assert r.status_code == 201, r.text
        return dict(r.json())

    def generate(self, **extra: Any) -> Any:
        return self.env.req(
            "POST", "/plans/generate", self.env.student, json={"role_id": self.role, **extra}
        )

    def resource(self, skill: Skill, title: str = "Python Basics", approve: bool = True) -> int:
        r = self.env.req(
            "POST", "/admin/learning-resources", self.env.admin,
            json={"skill_id": skill.id, "title": title, "url": "https://example.com/x"},
        )
        assert r.status_code == 201, r.text
        rid = int(r.json()["id"])
        if approve:
            a = self.env.req("POST", f"/admin/learning-resources/{rid}/approve", self.env.admin)
            assert a.status_code == 200, a.text
        return rid


@pytest.fixture
def sc(env: Env) -> Scenario:
    """Scenario with a role and a student with evidence."""
    return Scenario(env)


def all_items(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten plan items."""
    return [i for w in plan["weeks"] for i in w["items"]]


# ---- goals --------------------------------------------------------------------------------
def test_goals_crud_and_validation(env: Env) -> None:
    r1, r2 = env.role("R1"), env.role("R2")
    assert env.req("GET", "/students/me/career-goals", env.student).json() == []
    put = env.req(
        "PUT", "/students/me/career-goals", env.student,
        json=[{"career_role_id": r2, "priority": 2}, {"career_role_id": r1, "priority": 1}],
    )
    assert put.status_code == 200
    assert put.json() == [
        {"career_role_id": r1, "role_name": "R1", "priority": 1},
        {"career_role_id": r2, "role_name": "R2", "priority": 2},
    ]
    dup_role = [{"career_role_id": r1, "priority": 1}, {"career_role_id": r1, "priority": 2}]
    assert env.req("PUT", "/students/me/career-goals", env.student, json=dup_role).status_code == 422
    dup_prio = [{"career_role_id": r1, "priority": 1}, {"career_role_id": r2, "priority": 1}]
    assert env.req("PUT", "/students/me/career-goals", env.student, json=dup_prio).status_code == 422
    bad = [{"career_role_id": r1, "priority": 0}]
    assert env.req("PUT", "/students/me/career-goals", env.student, json=bad).status_code == 422
    missing = [{"career_role_id": 9999, "priority": 1}]
    assert env.req("PUT", "/students/me/career-goals", env.student, json=missing).status_code == 404
    # failed attempts leave goals untouched
    assert len(env.req("GET", "/students/me/career-goals", env.student).json()) == 2
    assert env.req("PUT", "/students/me/career-goals", env.student, json=[]).json() == []
    assert "CAREER_GOALS_UPDATE" in env.actions()


def test_goal_role_must_be_active_and_visible(env: Env) -> None:
    dept = env.dept(env.a, "ME")
    other_dept_role = env.role("Dept Role", department_id=dept.id)
    inactive = env.role("Inactive", is_active=False)
    env.student_row(env.student)
    for rid in (other_dept_role, inactive):
        r = env.req(
            "PUT", "/students/me/career-goals", env.student,
            json=[{"career_role_id": rid, "priority": 1}],
        )
        assert r.status_code == 404


def test_career_role_additive_fields(env: Env, sc: Scenario) -> None:
    other = env.role("Other")
    env.req(
        "PUT", "/students/me/career-goals", env.student,
        json=[{"career_role_id": sc.role, "priority": 1}],
    )
    listing = {r["id"]: r for r in env.req("GET", "/career-roles", env.student).json()}
    assert listing[sc.role]["is_goal"] is True and listing[other]["is_goal"] is False
    assert {"id", "department_id", "name", "description", "is_active"} <= set(listing[sc.role])
    detail = env.req("GET", f"/career-roles/{sc.role}", env.student).json()
    assert detail["is_goal"] is True and detail["my_readiness"] is None
    assert len(detail["skills"]) == 3
    computed = sc.compute()
    detail = env.req("GET", f"/career-roles/{sc.role}", env.student).json()
    mine = detail["my_readiness"]
    assert mine["overall"] == computed["overall"] and mine["level"] == computed["level"]
    assert mine["rule_version"] == 1 and "computed_at" in mine and "coverage" in mine
    # admin view of roles is unchanged
    admin_list = env.req("GET", "/admin/career-roles", env.admin).json()
    assert "is_goal" not in admin_list[0]


# ---- resources ----------------------------------------------------------------------------
def test_resource_approval_flow(env: Env, sc: Scenario) -> None:
    rid = sc.resource(env.py, approve=False)
    assert env.req("GET", "/learning-resources", env.student).json() == []
    listed = env.req("GET", "/admin/learning-resources", env.admin).json()
    assert listed[0]["is_approved"] is False and listed[0]["skill_name"] == "Python"
    assert listed[0]["created_by"] == env.admin.id
    # faculty may create/list but not approve
    f = env.req(
        "POST", "/admin/learning-resources", env.faculty,
        json={"skill_id": env.sql.id, "title": "SQL", "url": "http://example.com/sql"},
    )
    assert f.status_code == 201
    assert env.req("POST", f"/admin/learning-resources/{rid}/approve", env.faculty).status_code == 403
    assert env.req("POST", f"/admin/learning-resources/{rid}/unapprove", env.faculty).status_code == 403
    ok = env.req("POST", f"/admin/learning-resources/{rid}/approve", env.admin)
    assert ok.json()["is_approved"] is True and ok.json()["approved_by"] == env.admin.id
    assert ok.json()["approved_at"] is not None
    pub = env.req("GET", f"/learning-resources?skill_id={env.py.id}", env.student).json()
    assert pub == [{
        "id": rid, "skill_id": env.py.id, "skill_name": "Python", "title": "Python Basics",
        "url": "https://example.com/x", "description": None,
    }]
    assert env.req("GET", f"/learning-resources?skill_id={env.sql.id}", env.student).json() == []
    assert len(env.req("GET", "/admin/learning-resources?approved=true", env.admin).json()) == 1
    assert len(env.req("GET", "/admin/learning-resources?approved=false", env.admin).json()) == 1
    # title change keeps approval, url change resets it
    p = env.req("PUT", f"/admin/learning-resources/{rid}", env.faculty, json={"title": "New"})
    assert p.json()["is_approved"] is True and p.json()["title"] == "New"
    p = env.req(
        "PUT", f"/admin/learning-resources/{rid}", env.faculty, json={"url": "https://example.com/y"}
    )
    assert p.json()["is_approved"] is False and p.json()["approved_by"] is None
    assert env.req("GET", "/learning-resources", env.student).json() == []
    env.req("POST", f"/admin/learning-resources/{rid}/approve", env.admin)
    p = env.req(
        "PUT", f"/admin/learning-resources/{rid}", env.admin, json={"skill_id": env.sql.id}
    )
    assert p.json()["is_approved"] is False and p.json()["skill_id"] == env.sql.id
    env.req("POST", f"/admin/learning-resources/{rid}/approve", env.admin)
    un = env.req("POST", f"/admin/learning-resources/{rid}/unapprove", env.admin)
    assert un.json()["is_approved"] is False
    assert env.req("DELETE", f"/admin/learning-resources/{rid}", env.faculty).status_code == 204
    assert env.req("DELETE", f"/admin/learning-resources/{rid}", env.faculty).status_code == 404
    acts = env.actions()
    for a in ("LEARNING_RESOURCE_CREATE", "LEARNING_RESOURCE_UPDATE", "LEARNING_RESOURCE_DELETE",
              "LEARNING_RESOURCE_APPROVE", "LEARNING_RESOURCE_UNAPPROVE"):
        assert a in acts


def test_resource_validation(env: Env) -> None:
    for url in ("ftp://x.com/a", "javascript:alert(1)", "not a url", "https://"):
        r = env.req(
            "POST", "/admin/learning-resources", env.admin,
            json={"skill_id": env.py.id, "title": "t", "url": url},
        )
        assert r.status_code == 422, url
    bad_skill = env.req(
        "POST", "/admin/learning-resources", env.admin,
        json={"skill_id": 9999, "title": "t", "url": "https://a.com"},
    )
    assert bad_skill.status_code == 422
    ok = env.req(
        "POST", "/admin/learning-resources", env.admin,
        json={"skill_id": env.py.id, "title": "t", "url": "https://a.com"},
    )
    rid = ok.json()["id"]
    assert env.req(
        "PUT", f"/admin/learning-resources/{rid}", env.admin, json={"url": "gopher://x"}
    ).status_code == 422
    assert env.req(
        "PUT", f"/admin/learning-resources/{rid}", env.admin, json={"skill_id": 9999}
    ).status_code == 422


def test_resource_role_guards(env: Env) -> None:
    for user in (env.student, env.tpo, env.hod):
        assert env.req("GET", "/admin/learning-resources", user).status_code == 403
    assert env.req("GET", "/learning-resources", env.admin).status_code == 403
    assert env.req("GET", "/learning-resources", env.faculty).status_code == 403
    assert env.client.get("/api/v1/learning-resources").status_code == 401


# ---- plans --------------------------------------------------------------------------------
def test_generate_requires_gaps_and_role_visibility(env: Env, sc: Scenario) -> None:
    r = sc.generate()
    assert r.status_code == 409
    assert r.json() == {"detail": "Compute readiness for this role first"}
    assert env.req("POST", "/plans/generate", env.student, json={"role_id": 9999}).status_code == 404
    assert sc.generate(skills_per_week=0).status_code == 422
    assert sc.generate(skills_per_week=6).status_code == 422
    assert env.req("GET", "/plans/me", env.student).status_code == 404


def test_generate_plan_structure(env: Env, sc: Scenario) -> None:
    sc.resource(env.py, "Python Basics")
    sc.resource(env.py, "Python Advanced")
    sc.resource(env.py, "Python Third")
    sc.resource(env.sql, "Hidden SQL", approve=False)
    computed = sc.compute()
    r = sc.generate()
    assert r.status_code == 201, r.text
    plan = r.json()
    assert plan["role_name"] == "Data Analyst" and plan["status"] == "ACTIVE"
    assert plan["duration_days"] == 30 and plan["skills_per_week"] == 2
    assert plan["baseline"]["readiness_score_id"] == computed["id"]
    assert plan["baseline"]["overall"] == computed["overall"]
    assert [w["week"] for w in plan["weeks"]] == [1, 2, 3, 4]
    w1 = plan["weeks"][0]["items"]
    assert w1[0]["kind"] == "ASSESS"
    assert w1[0]["task"] == "Take an assessment that covers Logic"
    learn = [i for i in w1 if i["kind"] == "LEARN"]
    assert [i["task"] for i in learn] == ["Study: Python Basics", "Study: Python Advanced"]
    assert learn[0]["resource"]["url"] == "https://example.com/x"
    practice = {i["skill_name"]: i for i in all_items(plan) if i["kind"] == "PRACTICE"}
    assert practice["Python"]["task"].startswith("Practise Python: Improve Python")
    assert practice["SQL"]["task"].endswith(" (no approved learning resource configured yet)")
    assert practice["SQL"]["resource"] is None
    assert "Hidden SQL" not in str(plan)
    assert [i["kind"] for i in plan["weeks"][3]["items"]] == ["REASSESS"]
    assert plan["unscheduled_skills"] == []
    assert [i["position"] for i in w1] == list(range(1, len(w1) + 1))
    total = len(all_items(plan))
    assert plan["progress"] == {"done": 0, "total": total, "percent": 0.0}
    assert env.req("GET", "/plans/me", env.student).json() == plan
    assert "LEARNING_PLAN_GENERATE" in env.actions()


def test_unscheduled_skills_reported(env: Env, sc: Scenario) -> None:
    sc.compute()
    # 1 GAP skill per week x 3 weeks = capacity 3; add 4 gap skills via extra role skills
    extra = [env.skill(env.a, env.cat1, f"Extra{i}") for i in range(3)]
    r = env.req(
        "PUT", f"/admin/career-roles/{sc.role}/skills", env.admin,
        json=[{"skill_id": env.py.id, "required_level": 90, "weight": 1}]
        + [{"skill_id": s.id, "required_level": 80, "weight": 1} for s in extra]
        + [{"skill_id": env.sql.id, "required_level": 85, "weight": 1}],
    )
    assert r.status_code == 200
    for s in extra:
        env.give_score(sc.row, s, 10)
    sc.compute()
    plan = sc.generate(skills_per_week=1).json()
    scheduled = {i["skill_name"] for i in all_items(plan) if i["kind"] == "PRACTICE"}
    assert len(scheduled) == 3
    assert len(plan["unscheduled_skills"]) == 2
    assert not scheduled & {u["skill_name"] for u in plan["unscheduled_skills"]}
    assert all(isinstance(u["gap"], float | int) for u in plan["unscheduled_skills"])


def test_generate_all_ready_makes_week4_only(env: Env, sc: Scenario) -> None:
    env.give_score(sc.row, env.logic, 90)
    # raise existing scores above required
    from app.models import StudentSkill
    for ss in env.db.execute(select(StudentSkill)).scalars():
        ss.score = 95
    env.db.commit()
    sc.compute()
    plan = sc.generate().json()
    assert [len(w["items"]) for w in plan["weeks"]] == [0, 0, 0, 1]


def test_generate_archives_previous_and_history(env: Env, sc: Scenario) -> None:
    sc.compute()
    first = sc.generate().json()
    other = env.role("Second Role")
    env.role_skills(other)
    env.req("POST", "/readiness/compute", env.student, json={"role_id": other})
    second = env.req("POST", "/plans/generate", env.student, json={"role_id": other}).json()
    hist = env.req("GET", "/plans/me/history", env.student).json()
    assert [h["id"] for h in hist] == [second["id"], first["id"]]
    assert [h["status"] for h in hist] == ["ACTIVE", "ARCHIVED"]
    assert hist[0]["role_name"] == "Second Role" and "progress" in hist[0]
    assert env.req("GET", "/plans/me", env.student).json()["id"] == second["id"]
    active = env.db.execute(
        select(LearningPlan).where(LearningPlan.status == "ACTIVE")
    ).scalars().all()
    assert len(active) == 1


def test_item_status_autocomplete_and_reactivate(env: Env, sc: Scenario) -> None:
    sc.compute()
    plan = sc.generate().json()
    items = all_items(plan)
    for it in items[:-1]:
        r = env.req("PATCH", f"/plans/items/{it['id']}", env.student, json={"status": "DONE"})
        assert r.status_code == 200 and r.json()["completed_at"] is not None
    mid = env.req("GET", "/plans/me", env.student).json()
    assert mid["status"] == "ACTIVE" and mid["progress"]["done"] == len(items) - 1
    ip = env.req("PATCH", f"/plans/items/{items[-1]['id']}", env.student,
                 json={"status": "IN_PROGRESS"})
    assert ip.json()["status"] == "IN_PROGRESS" and ip.json()["completed_at"] is None
    last = env.req("PATCH", f"/plans/items/{items[-1]['id']}", env.student,
                   json={"status": "DONE"})
    assert last.status_code == 200
    # completed plans are no longer "active" for GET /plans/me
    assert env.req("GET", "/plans/me", env.student).status_code == 404
    hist = env.req("GET", "/plans/me/history", env.student).json()
    assert hist[0]["status"] == "COMPLETED" and hist[0]["progress"]["percent"] == 100.0
    back = env.req("PATCH", f"/plans/items/{items[0]['id']}", env.student, json={"status": "TODO"})
    assert back.json()["completed_at"] is None
    assert env.req("GET", "/plans/me", env.student).json()["status"] == "ACTIVE"
    assert env.req("PATCH", f"/plans/items/{items[0]['id']}", env.student,
                   json={"status": "BOGUS"}).status_code == 422
    assert "LEARNING_PLAN_ITEM_STATUS" in env.actions()


def test_unapproved_after_generation_hidden_in_plan(env: Env, sc: Scenario) -> None:
    rid = sc.resource(env.py)
    sc.compute()
    plan = sc.generate().json()
    assert any(i["resource"] for i in all_items(plan))
    env.req("POST", f"/admin/learning-resources/{rid}/unapprove", env.admin)
    plan = env.req("GET", "/plans/me", env.student).json()
    assert not any(i["resource"] for i in all_items(plan))
    env.req("DELETE", f"/admin/learning-resources/{rid}", env.admin)
    assert env.req("GET", "/plans/me", env.student).status_code == 200


# ---- reassess -----------------------------------------------------------------------------
def test_reassess_deltas_and_rule_version(env: Env, sc: Scenario) -> None:
    assert env.req("POST", "/plans/me/reassess", env.student).status_code == 404
    baseline = sc.compute()
    sc.generate()
    from app.models import StudentSkill
    for ss in env.db.execute(select(StudentSkill)).scalars():
        if ss.skill_id == env.py.id:
            ss.score = 65
    env.give_score(sc.row, env.logic, 55)
    env.db.commit()
    r = env.req("POST", "/plans/me/reassess", env.student)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["baseline"]["overall"] == baseline["overall"]
    assert body["current"]["id"] != baseline["id"]
    assert body["overall_delta"] == round(body["current"]["overall"] - baseline["overall"], 2)
    assert body["overall_delta"] > 0
    assert body["rule_version_changed"] is False
    ch = {c["skill_name"]: c for c in body["skill_changes"]}
    assert ch["Python"] == {"skill_id": env.py.id, "skill_name": "Python",
                            "before": 40.0, "after": 65.0, "delta": 25.0}
    assert ch["Logic"]["before"] is None and ch["Logic"]["after"] == 55.0
    assert ch["Logic"]["delta"] is None
    assert ch["SQL"]["delta"] == 0.0
    # new rule version flips the flag
    env.active_rule()
    again = env.req("POST", "/plans/me/reassess", env.student).json()
    assert again["rule_version_changed"] is True and again["current"]["rule_version"] == 2
    assert "LEARNING_PLAN_REASSESS" in env.actions()


def test_reassess_without_rule_is_409(env: Env, sc: Scenario) -> None:
    sc.compute()
    sc.generate()
    from app.models import ReadinessRule
    for rule in env.db.execute(select(ReadinessRule)).scalars():
        rule.is_active = False
    env.db.commit()
    assert env.req("POST", "/plans/me/reassess", env.student).status_code == 409


# ---- isolation and guards -------------------------------------------------------------------
def test_cross_college_isolation(env: Env, sc: Scenario) -> None:
    rid = sc.resource(env.py)
    sc.compute()
    plan = sc.generate().json()
    item_id = all_items(plan)[0]["id"]
    # college B student and admin
    env.student_row(env.student_b)
    b_cat = env.category(env.b, "Tech")
    b_skill = env.skill(env.b, b_cat, "Python")
    assert env.req("GET", "/learning-resources", env.student_b).json() == []
    assert env.req("GET", "/admin/learning-resources", env.admin_b).json() == []
    for method, path in (
        ("PUT", f"/admin/learning-resources/{rid}"),
        ("DELETE", f"/admin/learning-resources/{rid}"),
        ("POST", f"/admin/learning-resources/{rid}/approve"),
        ("POST", f"/admin/learning-resources/{rid}/unapprove"),
    ):
        kw: dict[str, Any] = {"json": {"title": "x"}} if method == "PUT" else {}
        assert env.req(method, path, env.admin_b, **kw).status_code == 404, path
    assert env.req(
        "POST", "/admin/learning-resources", env.admin_b,
        json={"skill_id": env.py.id, "title": "t", "url": "https://a.com"},
    ).status_code == 422
    assert env.req("PATCH", f"/plans/items/{item_id}", env.student_b,
                   json={"status": "DONE"}).status_code == 404
    assert env.req("GET", "/plans/me", env.student_b).status_code == 404
    assert env.req("GET", "/plans/me/history", env.student_b).json() == []
    assert env.req("POST", "/plans/me/reassess", env.student_b).status_code == 404
    assert env.req("POST", "/plans/generate", env.student_b, json={"role_id": sc.role}
                   ).status_code == 404
    assert env.req("PUT", "/students/me/career-goals", env.student_b,
                   json=[{"career_role_id": sc.role, "priority": 1}]).status_code == 404
    assert env.req("GET", f"/career-roles/{sc.role}", env.student_b).status_code == 404
    # same college, other student cannot touch the item either
    env.student_row(env.student2)
    assert env.req("PATCH", f"/plans/items/{item_id}", env.student2,
                   json={"status": "DONE"}).status_code == 404
    assert b_skill.id != env.py.id


def test_role_guards(env: Env, sc: Scenario) -> None:
    for user in (env.admin, env.faculty, env.tpo, env.hod):
        assert env.req("GET", "/plans/me", user).status_code == 403
        assert env.req("GET", "/students/me/career-goals", user).status_code == 403
        assert env.req("POST", "/plans/generate", user, json={"role_id": sc.role}
                       ).status_code == 403
        assert env.req("POST", "/plans/me/reassess", user).status_code == 403
        assert env.req("PATCH", "/plans/items/1", user, json={"status": "DONE"}).status_code == 403
    assert env.client.get("/api/v1/plans/me").status_code == 401


def test_no_probability_wording_and_no_extra_items(env: Env, sc: Scenario) -> None:
    sc.resource(env.py)
    sc.compute()
    plan = sc.generate().json()
    reassess = env.req("POST", "/plans/me/reassess", env.student).json()
    text = (str(plan) + str(reassess)).lower()
    for word in ("probability", "chance", "likelihood", "will be placed", "placement"):
        assert word not in text
    items = env.db.execute(select(LearningPlanItem)).scalars().all()
    assert all(i.college_id == env.a.id for i in items)
    assert env.db.execute(select(AuditLog).where(AuditLog.action == "LEARNING_PLAN_GENERATE")
                          ).scalars().all()
    assert UserRole.STUDENT is not None
