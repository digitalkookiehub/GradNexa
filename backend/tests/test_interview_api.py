"""Mock interview API tests: lifecycle, visibility, authoring, isolation, audit."""
import json
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import College, InterviewQuestion, User
from tests.test_readiness_api import Env

Headers = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]
RUBRIC = [
    {"concept": "indexing", "keywords": ["index", "b-tree"], "weight": 2},
    {"concept": "joins", "keywords": ["join"], "weight": 1},
]


@pytest.fixture
def env(
    client: TestClient, db: Session, auth_headers: Headers, make_user: MakeUser,
    college: College, other_college: College,
) -> Env:
    """College A/B scenario."""
    return Env(client, db, auth_headers, make_user, college, other_college)


def qbody(**over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "competency": "Databases", "prompt": "Explain indexing.", "rubric": RUBRIC,
        "min_words": 3,
    }
    body.update(over)
    return body


def author(env: Env, user: User | None = None, **over: Any) -> dict[str, Any]:
    r = env.req("POST", "/admin/interview-questions", user or env.admin, json=qbody(**over))
    assert r.status_code == 201, r.text
    return dict(r.json())


def start(env: Env, role_id: int, user: User | None = None, **body: Any) -> Any:
    return env.req(
        "POST", "/interviews", user or env.student, json={"role_id": role_id, **body}
    )


def setup(env: Env, n: int = 2) -> tuple[int, list[dict[str, Any]]]:
    role = env.role("Data Analyst")
    qs = [author(env, role_id=role, prompt=f"Q{i}") for i in range(n)]
    return role, qs


def no_leak(*bodies: Any) -> None:
    text = json.dumps(bodies)
    for forbidden in ('"rubric"', "keywords", "b-tree", '"weight"'):
        assert forbidden not in text


# ---- lifecycle ---------------------------------------------------------------------------
def test_full_lifecycle(env: Env) -> None:
    role, _ = setup(env)
    r = start(env, role)
    assert r.status_code == 201, r.text
    iv = r.json()
    assert iv["status"] == "IN_PROGRESS" and iv["role_name"] == "Data Analyst"
    assert iv["completed_at"] is None
    assert [q["position"] for q in iv["questions"]] == [1, 2]
    assert iv["questions"][0]["answer_text"] is None
    no_leak(iv)
    again = start(env, role)
    assert again.status_code == 200 and again.json()["id"] == iv["id"]
    ids = [q["answer_id"] for q in iv["questions"]]
    s = env.req(
        "PUT", f"/interviews/{iv['id']}/answers", env.student,
        json={"answers": [
            {"answer_id": ids[0], "answer_text": "Use an index on the column"},
            {"answer_id": ids[1], "answer_text": "ok"},
        ]},
    )
    assert s.status_code == 200 and s.json() == {"saved": 2}
    got = env.req("GET", f"/interviews/{iv['id']}", env.student).json()
    assert got["questions"][0]["answer_text"] == "Use an index on the column"
    no_leak(got)
    assert env.req("GET", f"/interviews/{iv['id']}/result", env.student).status_code == 404
    f = env.req("POST", f"/interviews/{iv['id']}/finish", env.student)
    assert f.status_code == 200, f.text
    res = f.json()
    no_leak(res)
    assert res["overall"] == 33.34 and res["scoring_version"] == "rubric-1"
    assert res["role_name"] == "Data Analyst"
    assert res["competency_scores"] == [
        {"competency": "Databases", "score": 33.34, "max": 100, "questions": 2}
    ]
    pq = res["per_question"]
    assert pq[0]["score"] == 66.67 and pq[0]["covered_concepts"] == ["indexing"]
    assert pq[0]["missed_concepts"] == ["joins"] and pq[0]["answered"] is True
    assert pq[0]["too_short"] is False and pq[1]["too_short"] is True
    assert "personality" in res["disclaimer"] and "do not assess" in res["disclaimer"]
    f2 = env.req("POST", f"/interviews/{iv['id']}/finish", env.student).json()
    assert f2 == res
    assert env.req("GET", f"/interviews/{iv['id']}/result", env.student).json() == res
    c = env.req(
        "PUT", f"/interviews/{iv['id']}/answers", env.student,
        json={"answers": [{"answer_id": ids[0], "answer_text": "x"}]},
    )
    assert c.status_code == 409
    done = env.req("GET", f"/interviews/{iv['id']}", env.student).json()
    assert done["status"] == "COMPLETED" and done["completed_at"]
    assert start(env, role).status_code == 201
    lst = env.req("GET", "/interviews", env.student).json()
    assert len(lst) == 2 and lst[0]["status"] == "IN_PROGRESS" and lst[0]["overall"] is None
    assert lst[1]["overall"] == 33.34 and lst[1]["role_name"] == "Data Analyst"
    no_leak(lst)
    assert {"INTERVIEW_START", "INTERVIEW_FINISH"} <= set(env.actions())
    assert env.actions().count("INTERVIEW_FINISH") == 1


def test_finish_with_no_answers_scores_zero(env: Env) -> None:
    role, _ = setup(env, 1)
    iv = start(env, role).json()
    res = env.req("POST", f"/interviews/{iv['id']}/finish", env.student).json()
    assert res["overall"] == 0.0 and res["per_question"][0]["answered"] is False


def test_question_selection_role_first_then_generic_and_count(env: Env) -> None:
    role = env.role("R1")
    other = env.role("R2")
    generic = author(env, prompt="generic")
    author(env, role_id=other, prompt="other role")
    mine = author(env, role_id=role, prompt="mine")
    inactive = author(env, role_id=role, prompt="inactive")
    env.req("DELETE", f"/admin/interview-questions/{inactive['id']}", env.admin)
    iv = start(env, role, question_count=5).json()
    assert [q["prompt"] for q in iv["questions"]] == ["mine", "generic"]
    assert [q["question_id"] for q in iv["questions"]] == [mine["id"], generic["id"]]
    env.req("POST", f"/interviews/{iv['id']}/finish", env.student)
    one = start(env, role, question_count=1).json()
    assert [q["prompt"] for q in one["questions"]] == ["mine"]


def test_no_questions_409_and_validation(env: Env) -> None:
    role = env.role("Empty")
    r = start(env, role)
    assert r.status_code == 409
    assert r.json() == {"detail": "No interview questions configured for this role"}
    assert start(env, role, question_count=0).status_code == 422
    assert start(env, role, question_count=11).status_code == 422
    assert start(env, 99999).status_code == 404


def test_answer_validation(env: Env) -> None:
    role, _ = setup(env, 1)
    iv = start(env, role).json()
    aid = iv["questions"][0]["answer_id"]
    base = f"/interviews/{iv['id']}/answers"

    def put(items: list[dict[str, Any]]) -> Any:
        return env.req("PUT", base, env.student, json={"answers": items})

    assert put([{"answer_id": 9999, "answer_text": "x"}]).status_code == 422
    assert put([{"answer_id": aid, "answer_text": "x" * 10001}]).status_code == 422
    assert put([{"answer_id": aid, "answer_text": "x" * 10000}]).status_code == 200
    bad = put([
        {"answer_id": aid, "answer_text": "changed"}, {"answer_id": 9999, "answer_text": "y"}
    ])
    assert bad.status_code == 422
    got = env.req("GET", f"/interviews/{iv['id']}", env.student).json()
    assert got["questions"][0]["answer_text"] == "x" * 10000


def test_role_visibility_404(env: Env) -> None:
    dept1, dept2 = env.dept(env.a, "CS"), env.dept(env.a, "EC")
    env.student_row(env.student, dept1)
    hidden = env.role("Hidden", department_id=dept2.id)
    author(env, role_id=hidden)
    assert start(env, hidden).status_code == 404
    visible = env.role("Visible", department_id=dept1.id)
    author(env, role_id=visible)
    assert start(env, visible).status_code == 201
    inactive = env.role("Off", is_active=False)
    author(env, role_id=inactive)
    assert start(env, inactive).status_code == 404


def test_students_see_only_own_and_cross_college(env: Env) -> None:
    role, _ = setup(env, 1)
    iv = start(env, role).json()
    base = f"/interviews/{iv['id']}"
    for user in (env.student2, env.student_b):
        assert env.req("GET", base, user).status_code == 404
        assert env.req("POST", base + "/finish", user).status_code == 404
        assert env.req("GET", base + "/result", user).status_code == 404
        assert env.req("PUT", base + "/answers", user, json={"answers": []}).status_code == 404
        assert env.req("GET", "/interviews", user).json() == []
    assert start(env, role, user=env.student_b).status_code == 404


def test_student_role_guards(env: Env) -> None:
    role, _ = setup(env, 1)
    for u in (env.admin, env.faculty, env.tpo, env.hod, env.super_admin):
        assert start(env, role, user=u).status_code == 403
        assert env.req("GET", "/interviews", u).status_code == 403
    assert env.client.get("/api/v1/interviews").status_code == 401


# ---- admin question bank -------------------------------------------------------------------
def test_staff_authoring_and_audit(env: Env) -> None:
    role = env.role("Dev")
    q = author(env, env.faculty, role_id=role, skill_id=env.py.id)
    assert q["role_name"] == "Dev" and q["created_by"] == env.faculty.id and q["is_active"]
    assert q["rubric"][0]["keywords"] == ["index", "b-tree"]
    u = env.req(
        "PUT", f"/admin/interview-questions/{q['id']}", env.admin,
        json={"prompt": "New prompt", "min_words": 0, "skill_id": None},
    )
    assert u.status_code == 200
    assert u.json()["prompt"] == "New prompt" and u.json()["skill_id"] is None
    assert u.json()["role_id"] == role and u.json()["competency"] == "Databases"
    u2 = env.req(
        "PUT", f"/admin/interview-questions/{q['id']}", env.admin,
        json={"rubric": [{"concept": "c", "keywords": [" k "], "weight": 1}], "role_id": None},
    )
    assert u2.json()["rubric"] == [{"concept": "c", "keywords": ["k"], "weight": 1.0}]
    assert u2.json()["role_id"] is None and u2.json()["role_name"] is None
    assert env.req("DELETE", f"/admin/interview-questions/{q['id']}", env.admin).status_code == 204
    assert {
        "INTERVIEW_QUESTION_CREATE", "INTERVIEW_QUESTION_UPDATE", "INTERVIEW_QUESTION_DELETE"
    } <= set(env.actions())
    listing = env.req("GET", "/admin/interview-questions", env.faculty).json()
    assert len(listing) == 1 and listing[0]["is_active"] is False
    assert env.req("GET", "/admin/interview-questions?active=true", env.admin).json() == []
    assert len(env.req("GET", "/admin/interview-questions?active=false", env.admin).json()) == 1
    assert env.req("GET", "/admin/interview-questions?role_id=999", env.admin).json() == []


def test_question_validation_422(env: Env) -> None:
    foreign_skill = env.skill(env.b, env.category(env.b, "X"), "Foreign")
    bad: list[dict[str, Any]] = [
        {"rubric": []},
        {"rubric": [{"concept": "a", "keywords": [], "weight": 1}]},
        {"rubric": [{"concept": "a", "keywords": ["  "], "weight": 1}]},
        {"rubric": [{"concept": "a", "keywords": ["k"], "weight": 0}]},
        {"rubric": [{"concept": "a", "keywords": ["k"], "weight": -1}]},
        {"rubric": [{"concept": "  ", "keywords": ["k"], "weight": 1}]},
        {"competency": " "},
        {"prompt": ""},
        {"min_words": -1},
        {"role_id": 99999},
        {"skill_id": foreign_skill.id},
    ]
    for over in bad:
        r = env.req("POST", "/admin/interview-questions", env.admin, json=qbody(**over))
        assert r.status_code == 422, over
    assert env.db.execute(select(InterviewQuestion.id)).first() is None
    role = env.role("Dev")
    q = author(env, role_id=role)
    for over in ({"rubric": []}, {"competency": " "}, {"role_id": 99999}, {"skill_id": 99999}):
        r = env.req("PUT", f"/admin/interview-questions/{q['id']}", env.admin, json=over)
        assert r.status_code == 422, over


def test_authoring_guards_and_isolation(env: Env) -> None:
    for u in (env.student, env.tpo, env.hod, env.super_admin):
        assert env.req("GET", "/admin/interview-questions", u).status_code == 403
        assert env.req("POST", "/admin/interview-questions", u, json=qbody()).status_code == 403
        assert env.req("PUT", "/admin/interview-questions/1", u, json={}).status_code == 403
        assert env.req("DELETE", "/admin/interview-questions/1", u).status_code == 403
    assert env.client.get("/api/v1/admin/interview-questions").status_code == 401
    role = env.role("Dev")
    q = author(env, role_id=role)
    path = f"/admin/interview-questions/{q['id']}"
    assert env.req("GET", "/admin/interview-questions", env.admin_b).json() == []
    assert env.req("PUT", path, env.admin_b, json={"prompt": "z"}).status_code == 404
    assert env.req("DELETE", path, env.admin_b).status_code == 404
    assert env.req("PUT", "/admin/interview-questions/9999", env.admin, json={}).status_code == 404
    r = env.req("POST", "/admin/interview-questions", env.admin_b, json=qbody(role_id=role))
    assert r.status_code == 422
    assert env.req("POST", "/admin/interview-questions", env.admin_b, json=qbody()).status_code == 201
    assert len(env.req("GET", "/admin/interview-questions", env.admin).json()) == 1
    # college B's generic question never reaches a college A interview
    iv = start(env, role).json()
    assert [x["question_id"] for x in iv["questions"]] == [q["id"]]


def test_soft_delete_keeps_old_interviews_working(env: Env) -> None:
    role, qs = setup(env, 1)
    iv = start(env, role).json()
    aid = iv["questions"][0]["answer_id"]
    path = f"/admin/interview-questions/{qs[0]['id']}"
    assert env.req("DELETE", path, env.admin).status_code == 204
    assert env.db.get(InterviewQuestion, qs[0]["id"]) is not None
    assert env.req(
        "PUT", f"/interviews/{iv['id']}/answers", env.student,
        json={"answers": [{"answer_id": aid, "answer_text": "an index helps"}]},
    ).status_code == 200
    res = env.req("POST", f"/interviews/{iv['id']}/finish", env.student)
    assert res.status_code == 200 and res.json()["overall"] == 66.67
    assert start(env, role).status_code == 409


def test_edit_after_finish_does_not_change_stored_result(env: Env) -> None:
    role, qs = setup(env, 1)
    iv = start(env, role).json()
    aid = iv["questions"][0]["answer_id"]
    env.req(
        "PUT", f"/interviews/{iv['id']}/answers", env.student,
        json={"answers": [{"answer_id": aid, "answer_text": "index join"}]},
    )
    res = env.req("POST", f"/interviews/{iv['id']}/finish", env.student).json()
    env.req(
        "PUT", f"/admin/interview-questions/{qs[0]['id']}", env.admin,
        json={"rubric": [{"concept": "z", "keywords": ["zzz"], "weight": 1}]},
    )
    assert env.req("GET", f"/interviews/{iv['id']}/result", env.student).json() == res
    assert res["overall"] == 100.0


def test_disclaimer_makes_no_unsupported_claims(env: Env) -> None:
    role, _ = setup(env, 1)
    iv = start(env, role).json()
    res = env.req("POST", f"/interviews/{iv['id']}/finish", env.student).json()
    d = res["disclaimer"].lower()
    assert "coverage" in d and "do not assess" in d
    for word in ("personality", "confidence", "communication"):
        assert d.count(word) == 1 and d.index(word) > d.index("do not assess")
