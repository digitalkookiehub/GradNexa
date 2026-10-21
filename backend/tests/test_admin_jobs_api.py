"""Phase 7 admin API tests: companies, jobs lifecycle, skills, eligibility, access, isolation."""
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, College, User
from tests.test_readiness_api import Env

Headers = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


@pytest.fixture
def env(
    client: TestClient, db: Session, auth_headers: Headers, make_user: MakeUser,
    college: College, other_college: College,
) -> Env:
    return Env(client, db, auth_headers, make_user, college, other_college)


def company(env: Env, user: User | None = None, name: str = "Acme", **over: Any) -> dict[str, Any]:
    r = env.req("POST", "/admin/companies", user or env.admin, json={"name": name, **over})
    assert r.status_code == 201, r.text
    return dict(r.json())


def job(env: Env, cid: int, user: User | None = None, **over: Any) -> dict[str, Any]:
    body = {"company_id": cid, "title": "SDE", "body": "Build things", **over}
    r = env.req("POST", "/admin/jobs", user or env.admin, json=body)
    assert r.status_code == 201, r.text
    return dict(r.json())


def put_job(env: Env, jid: int, body: dict[str, Any]) -> Any:
    return env.req("PUT", f"/admin/jobs/{jid}", env.admin, json=body)


# ---------------- companies ----------------

def test_company_crud(env: Env) -> None:
    c = company(env, description="d", website="https://acme.com")
    assert c["is_active"] is True and c["job_count"] == 0 and c["website"] == "https://acme.com"
    assert company(env, env.tpo, name="Beta")["name"] == "Beta"
    listing = env.req("GET", "/admin/companies", env.admin).json()
    assert [x["name"] for x in listing] == ["Acme", "Beta"]
    r = env.req(
        "PUT", f"/admin/companies/{c['id']}", env.admin,
        json={"name": "Acme2", "is_active": False, "website": None},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Acme2" and r.json()["is_active"] is False
    assert r.json()["website"] is None
    assert env.req("DELETE", f"/admin/companies/{c['id']}", env.admin).status_code == 204
    assert env.req("DELETE", f"/admin/companies/{c['id']}", env.admin).status_code == 404


def test_company_duplicate_and_validation(env: Env) -> None:
    c = company(env)
    other = company(env, name="Other")
    assert env.req("POST", "/admin/companies", env.admin, json={"name": "acme"}).status_code == 409
    r = env.req("PUT", f"/admin/companies/{other['id']}", env.admin, json={"name": "Acme"})
    assert r.status_code == 409
    r = env.req("PUT", f"/admin/companies/{c['id']}", env.admin, json={"name": "Acme"})
    assert r.status_code == 200
    for bad in ("ftp://x.com", "acme.com", "javascript:alert(1)"):
        r = env.req("POST", "/admin/companies", env.admin, json={"name": "N", "website": bad})
        assert r.status_code == 422, bad
    assert env.req("POST", "/admin/companies", env.admin, json={"name": "  "}).status_code == 422
    r = env.req("PUT", f"/admin/companies/{c['id']}", env.admin, json={"website": "nope"})
    assert r.status_code == 422
    assert company(env, env.admin_b, name="Acme")["name"] == "Acme"


def test_company_delete_with_jobs(env: Env) -> None:
    c = company(env)
    job(env, c["id"])
    assert env.req("GET", "/admin/companies", env.admin).json()[0]["job_count"] == 1
    r = env.req("DELETE", f"/admin/companies/{c['id']}", env.admin)
    assert r.status_code == 409
    assert r.json() == {"detail": "Company has job postings; deactivate it instead"}


# ---------------- jobs ----------------

def test_job_lifecycle(env: Env) -> None:
    c = company(env)
    rid = env.role()
    j = job(env, c["id"], role_id=rid, application_deadline="2030-01-31")
    assert j["status"] == "DRAFT" and j["company_name"] == "Acme" and j["role_name"]
    assert j["skills"] == [] and j["eligibility"] is None and j["created_by"] == env.admin.id
    jid = j["id"]
    assert env.req("POST", f"/admin/jobs/{jid}/close", env.admin).status_code == 409
    r = env.req("POST", f"/admin/jobs/{jid}/publish", env.tpo)
    assert r.status_code == 200 and r.json()["status"] == "OPEN"
    assert env.req("POST", f"/admin/jobs/{jid}/publish", env.admin).status_code == 409
    d = env.req("DELETE", f"/admin/jobs/{jid}", env.admin)
    assert d.status_code == 409 and d.json() == {"detail": "Close the job instead"}
    r = put_job(env, jid, {"title": "SDE 2"})
    assert r.status_code == 200 and r.json()["title"] == "SDE 2"
    assert r.json()["role_id"] == rid
    r = env.req("POST", f"/admin/jobs/{jid}/close", env.admin)
    assert r.status_code == 200 and r.json()["status"] == "CLOSED"
    assert env.req("POST", f"/admin/jobs/{jid}/close", env.admin).status_code == 409
    assert env.req("POST", f"/admin/jobs/{jid}/publish", env.admin).status_code == 409
    assert put_job(env, jid, {"title": "x"}).status_code == 409
    assert env.req("DELETE", f"/admin/jobs/{jid}", env.admin).status_code == 409
    assert env.req("GET", f"/admin/jobs/{jid}", env.admin).json()["status"] == "CLOSED"


def test_job_null_clearing_and_validation(env: Env) -> None:
    c = company(env)
    rid = env.role()
    j = job(env, c["id"], role_id=rid, application_deadline="2030-01-31")
    jid = j["id"]
    r = put_job(env, jid, {"role_id": None, "application_deadline": None})
    assert r.status_code == 200
    assert r.json()["role_id"] is None and r.json()["role_name"] is None
    assert r.json()["application_deadline"] is None
    r = put_job(env, jid, {"body": "new"})
    assert r.json()["body"] == "new" and r.json()["title"] == "SDE"
    assert put_job(env, jid, {"title": None}).status_code == 422
    assert put_job(env, jid, {"title": " "}).status_code == 422
    assert put_job(env, jid, {"role_id": 9999}).status_code == 422
    other_role = env.req("POST", "/admin/career-roles", env.admin_b, json={"name": "BRole"})
    assert put_job(env, jid, {"role_id": other_role.json()["id"]}).status_code == 422


def test_job_create_validation(env: Env) -> None:
    c = company(env)
    base = {"company_id": c["id"], "title": "T", "body": "B"}

    def post(body: dict[str, Any]) -> int:
        return int(env.req("POST", "/admin/jobs", env.admin, json=body).status_code)

    assert post({**base, "role_id": 999}) == 422
    assert post({**base, "company_id": 999}) == 404
    assert post({**base, "title": " "}) == 422
    env.req("PUT", f"/admin/companies/{c['id']}", env.admin, json={"is_active": False})
    assert post(base) == 422


def test_job_delete_draft_and_list_filters(env: Env) -> None:
    c1, c2 = company(env), company(env, name="Beta")
    j1, j2 = job(env, c1["id"]), job(env, c2["id"], title="QA")
    env.req("POST", f"/admin/jobs/{j2['id']}/publish", env.admin)
    env.req("PUT", f"/admin/jobs/{j1['id']}/eligibility", env.admin, json={"max_arrears": 0})
    allj = env.req("GET", "/admin/jobs", env.admin).json()
    assert {x["id"] for x in allj} == {j1["id"], j2["id"]}
    by = {x["id"]: x for x in allj}
    assert by[j1["id"]]["has_eligibility_rule"] is True
    assert by[j2["id"]]["has_eligibility_rule"] is False
    by_company = env.req("GET", f"/admin/jobs?company_id={c2['id']}", env.admin).json()
    assert [x["id"] for x in by_company] == [j2["id"]]
    by_status = env.req("GET", "/admin/jobs?status=OPEN", env.admin).json()
    assert [x["id"] for x in by_status] == [j2["id"]]
    assert env.req("GET", "/admin/jobs?status=BOGUS", env.admin).status_code == 422
    env.req(
        "PUT", f"/admin/jobs/{j1['id']}/skills", env.admin,
        json=[{"skill_id": env.py.id, "required_level": 50, "weight": 1}],
    )
    assert env.req("DELETE", f"/admin/jobs/{j1['id']}", env.admin).status_code == 204
    assert env.req("GET", f"/admin/jobs/{j1['id']}", env.admin).status_code == 404


# ---------------- skills ----------------

def test_skills_bulk_replace(env: Env) -> None:
    j = job(env, company(env)["id"])
    path = f"/admin/jobs/{j['id']}/skills"
    r = env.req("PUT", path, env.admin, json=[
        {"skill_id": env.py.id, "required_level": 70, "weight": 2},
        {"skill_id": env.sql.id, "required_level": 0, "weight": 0.5},
    ])
    assert r.status_code == 200
    assert {(s["skill_name"], s["required_level"], s["weight"]) for s in r.json()} == {
        ("Python", 70, 2), ("SQL", 0, 0.5)}
    r = env.req(
        "PUT", path, env.admin,
        json=[{"skill_id": env.logic.id, "required_level": 100, "weight": 1}],
    )
    assert [s["skill_id"] for s in r.json()] == [env.logic.id]
    got = env.req("GET", f"/admin/jobs/{j['id']}", env.admin).json()
    assert [s["skill_id"] for s in got["skills"]] == [env.logic.id]
    assert env.req("PUT", path, env.admin, json=[]).json() == []


@pytest.mark.parametrize("item", [
    {"required_level": 101, "weight": 1},
    {"required_level": -1, "weight": 1},
    {"required_level": 50, "weight": 0},
    {"required_level": 50, "weight": -2},
])
def test_skills_invalid_values(env: Env, item: dict[str, Any]) -> None:
    j = job(env, company(env)["id"])
    body = [{**item, "skill_id": env.py.id}]
    assert env.req("PUT", f"/admin/jobs/{j['id']}/skills", env.admin, json=body).status_code == 422


def test_skills_duplicates_unknown_and_closed(env: Env) -> None:
    j = job(env, company(env)["id"])
    path = f"/admin/jobs/{j['id']}/skills"
    dup = [{"skill_id": env.py.id, "required_level": 50, "weight": 1}] * 2
    assert env.req("PUT", path, env.admin, json=dup).status_code == 422
    unknown = [{"skill_id": 99999, "required_level": 50, "weight": 1}]
    assert env.req("PUT", path, env.admin, json=unknown).status_code == 422
    cat = env.category(env.b, "T")
    sk = env.skill(env.b, cat, "BSkill")
    foreign = [{"skill_id": sk.id, "required_level": 50, "weight": 1}]
    assert env.req("PUT", path, env.admin, json=foreign).status_code == 422
    env.req("POST", f"/admin/jobs/{j['id']}/publish", env.admin)
    env.req("POST", f"/admin/jobs/{j['id']}/close", env.admin)
    ok = [{"skill_id": env.py.id, "required_level": 50, "weight": 1}]
    assert env.req("PUT", path, env.admin, json=ok).status_code == 409


# ---------------- eligibility ----------------

def test_eligibility_upsert_and_delete(env: Env) -> None:
    j = job(env, company(env)["id"])
    path = f"/admin/jobs/{j['id']}/eligibility"
    d1, d2 = env.dept(env.a, "CS"), env.dept(env.a, "EC")
    body = {
        "cgpa_min": 7.5, "cgpa_basis": "LATEST_SEMESTER", "max_arrears": 0,
        "attendance_min": 75, "department_ids": [d1.id, d2.id],
        "graduation_years": [2026, 2027], "custom_notes": ["  Bring ID  "],
    }
    r = env.req("PUT", path, env.admin, json=body)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["cgpa_min"] == 7.5 and isinstance(out["cgpa_min"], float)
    assert out["attendance_min"] == 75 and out["cgpa_basis"] == "LATEST_SEMESTER"
    assert out["department_ids"] == [
        {"id": d1.id, "name": "Dept CS"}, {"id": d2.id, "name": "Dept EC"}
    ]
    assert out["graduation_years"] == [2026, 2027] and out["custom_notes"] == ["Bring ID"]
    r = env.req(
        "PUT", path, env.admin, json={"cgpa_min": 6, "cgpa_basis": "AVERAGE_ALL_SEMESTERS"}
    )
    assert r.json() == {
        "cgpa_min": 6.0, "cgpa_basis": "AVERAGE_ALL_SEMESTERS", "max_arrears": None,
        "attendance_min": None, "department_ids": None, "graduation_years": None,
        "custom_notes": [],
    }
    got = env.req("GET", f"/admin/jobs/{j['id']}", env.admin).json()
    assert got["eligibility"]["cgpa_min"] == 6
    assert env.req("PUT", path, env.admin, json={}).status_code == 200
    assert env.req("DELETE", path, env.admin).status_code == 204
    assert env.req("DELETE", path, env.admin).status_code == 404
    assert env.req("GET", f"/admin/jobs/{j['id']}", env.admin).json()["eligibility"] is None


@pytest.mark.parametrize("body", [
    {"cgpa_min": 7},
    {"cgpa_basis": "LATEST_SEMESTER"},
    {"cgpa_min": None, "cgpa_basis": "LATEST_SEMESTER"},
    {"cgpa_min": 7, "cgpa_basis": "BOGUS"},
    {"cgpa_min": -0.1, "cgpa_basis": "LATEST_SEMESTER"},
    {"cgpa_min": 10.1, "cgpa_basis": "LATEST_SEMESTER"},
    {"max_arrears": -1},
    {"attendance_min": -1},
    {"attendance_min": 100.5},
    {"department_ids": []},
    {"graduation_years": []},
    {"graduation_years": [1989]},
    {"graduation_years": [2101]},
    {"department_ids": [99999]},
    {"custom_notes": [" "]},
    {"custom_notes": ["x" * 501]},
    {"custom_notes": ["n"] * 21},
    {"unknown_field": 1},
])
def test_eligibility_validation_matrix(env: Env, body: dict[str, Any]) -> None:
    j = job(env, company(env)["id"])
    r = env.req("PUT", f"/admin/jobs/{j['id']}/eligibility", env.admin, json=body)
    assert r.status_code == 422, r.text
    assert "detail" in r.json()


def test_eligibility_boundaries_and_foreign_department(env: Env) -> None:
    j = job(env, company(env)["id"])
    path = f"/admin/jobs/{j['id']}/eligibility"
    ok = {
        "cgpa_min": 10, "cgpa_basis": "LATEST_SEMESTER", "max_arrears": 0,
        "attendance_min": 100, "graduation_years": [1990, 2100],
        "custom_notes": ["x" * 500] * 20,
    }
    assert env.req("PUT", path, env.admin, json=ok).status_code == 200
    low = {"cgpa_min": 0, "cgpa_basis": "LATEST_SEMESTER"}
    assert env.req("PUT", path, env.admin, json=low).status_code == 200
    foreign = env.dept(env.b, "ME")
    r = env.req("PUT", path, env.admin, json={"department_ids": [foreign.id]})
    assert r.status_code == 422


# ---------------- access, isolation, audit ----------------

def test_role_guards(env: Env) -> None:
    c = company(env)
    j = job(env, c["id"])
    jid = j["id"]
    calls: list[tuple[str, str, Any]] = [
        ("GET", "/admin/companies", None),
        ("POST", "/admin/companies", {"name": "X"}),
        ("PUT", f"/admin/companies/{c['id']}", {"name": "Y"}),
        ("DELETE", f"/admin/companies/{c['id']}", None),
        ("GET", "/admin/jobs", None),
        ("POST", "/admin/jobs", {"company_id": c["id"], "title": "t", "body": "b"}),
        ("GET", f"/admin/jobs/{jid}", None),
        ("PUT", f"/admin/jobs/{jid}", {"title": "z"}),
        ("DELETE", f"/admin/jobs/{jid}", None),
        ("POST", f"/admin/jobs/{jid}/publish", None),
        ("POST", f"/admin/jobs/{jid}/close", None),
        ("PUT", f"/admin/jobs/{jid}/skills", []),
        ("PUT", f"/admin/jobs/{jid}/eligibility", {}),
        ("DELETE", f"/admin/jobs/{jid}/eligibility", None),
    ]
    for user in (env.student, env.faculty, env.hod, env.super_admin):
        for method, path, body in calls:
            kw = {"json": body} if body is not None else {}
            r = env.req(method, path, user, **kw)
            assert r.status_code == 403, (user.role, method, path)
    assert env.client.get("/api/v1/admin/jobs").status_code == 401
    assert env.req("GET", "/admin/jobs", env.tpo).status_code == 200
    assert env.req("PUT", f"/admin/jobs/{jid}/eligibility", env.tpo, json={}).status_code == 200


def test_cross_college_isolation(env: Env) -> None:
    c = company(env)
    j = job(env, c["id"])
    jid = j["id"]
    cb = company(env, env.admin_b, name="BCo")
    jb = job(env, cb["id"], env.admin_b)
    assert [x["id"] for x in env.req("GET", "/admin/companies", env.admin_b).json()] == [cb["id"]]
    assert [x["id"] for x in env.req("GET", "/admin/jobs", env.tpo_b).json()] == [jb["id"]]
    assert env.req("GET", f"/admin/jobs?company_id={c['id']}", env.admin_b).json() == []
    calls: list[tuple[str, str, Any]] = [
        ("PUT", f"/admin/companies/{c['id']}", {"name": "Hack"}),
        ("DELETE", f"/admin/companies/{c['id']}", None),
        ("GET", f"/admin/jobs/{jid}", None),
        ("PUT", f"/admin/jobs/{jid}", {"title": "Hack"}),
        ("DELETE", f"/admin/jobs/{jid}", None),
        ("POST", f"/admin/jobs/{jid}/publish", None),
        ("POST", f"/admin/jobs/{jid}/close", None),
        ("PUT", f"/admin/jobs/{jid}/skills", []),
        ("PUT", f"/admin/jobs/{jid}/eligibility", {}),
        ("DELETE", f"/admin/jobs/{jid}/eligibility", None),
    ]
    for method, path, body in calls:
        kw = {"json": body} if body is not None else {}
        r = env.req(method, path, env.admin_b, **kw)
        assert r.status_code == 404, (method, path, r.text)
    r = env.req(
        "POST", "/admin/jobs", env.admin_b,
        json={"company_id": c["id"], "title": "t", "body": "b"},
    )
    assert r.status_code == 404
    got = env.req("GET", f"/admin/jobs/{jid}", env.admin).json()
    assert got["title"] == "SDE" and got["status"] == "DRAFT"


def test_audit_rows(env: Env) -> None:
    c = company(env)
    env.req("PUT", f"/admin/companies/{c['id']}", env.admin, json={"description": "x"})
    j = job(env, c["id"])
    jid = j["id"]
    put_job(env, jid, {"title": "T2"})
    env.req(
        "PUT", f"/admin/jobs/{jid}/skills", env.admin,
        json=[{"skill_id": env.py.id, "required_level": 50, "weight": 1}],
    )
    env.req("PUT", f"/admin/jobs/{jid}/eligibility", env.admin, json={"max_arrears": 1})
    env.req("DELETE", f"/admin/jobs/{jid}/eligibility", env.admin)
    env.req("POST", f"/admin/jobs/{jid}/publish", env.admin)
    env.req("POST", f"/admin/jobs/{jid}/close", env.admin)
    j2 = job(env, c["id"], title="Other")
    env.req("DELETE", f"/admin/jobs/{j2['id']}", env.admin)
    c2 = company(env, name="Tmp")
    env.req("DELETE", f"/admin/companies/{c2['id']}", env.admin)
    assert {
        "COMPANY_CREATE", "COMPANY_UPDATE", "COMPANY_DELETE", "JOB_CREATE", "JOB_UPDATE",
        "JOB_DELETE", "JOB_PUBLISH", "JOB_CLOSE", "JOB_SKILLS_REPLACE", "JOB_ELIGIBILITY_SET",
        "JOB_ELIGIBILITY_DELETE",
    } <= set(env.actions())
    row = env.db.execute(select(AuditLog).where(AuditLog.action == "JOB_PUBLISH")).scalar_one()
    assert row.college_id == env.a.id and row.user_id == env.admin.id
    assert row.resource_id == str(jid)
