"""Phase 2 API tests: skills, authoring, attempts, results, isolation, audit."""
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AssessmentAttempt,
    AuditLog,
    College,
    Department,
    Student,
    StudentSkill,
    User,
    UserRole,
)

Headers = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]
API = "/api/v1"


class Env:
    """Shared scenario: college A with admin/faculty/student, college B with admin/student."""

    def __init__(
        self, client: TestClient, db: Session, h: Headers, make_user: MakeUser,
        a: College, b: College,
    ) -> None:
        self.client, self.db, self.h = client, db, h
        self.admin = make_user(a, UserRole.ADMIN)
        self.faculty = make_user(a, UserRole.FACULTY)
        self.student = make_user(a, UserRole.STUDENT)
        self.student2 = make_user(a, UserRole.STUDENT, email="s2@a.example.com")
        self.admin_b = make_user(b, UserRole.ADMIN)
        self.student_b = make_user(b, UserRole.STUDENT)
        self.college_a, self.college_b = a, b

    def req(self, method: str, path: str, user: User, **kw: Any) -> Any:
        return self.client.request(method, API + path, headers=self.h(user), **kw)

    def mk_skill(self, user: User, name: str = "Python", cat: str = "Tech") -> tuple[int, int]:
        c = self.req("POST", "/admin/skill-categories", user, json={"name": cat})
        cat_id = c.json()["id"] if c.status_code == 201 else self.req(
            "GET", "/skill-categories", user).json()[0]["id"]
        s = self.req("POST", "/admin/skills", user, json={"category_id": cat_id, "name": name})
        assert s.status_code == 201, s.text
        return cat_id, s.json()["id"]

    def mk_assessment(self, user: User, **over: Any) -> int:
        body = {"title": "Quiz", "type": "TECHNICAL", **over}
        r = self.req("POST", "/admin/assessments", user, json=body)
        assert r.status_code == 201, r.text
        return int(r.json()["id"])

    def add_q(
        self, user: User, aid: int, skill: int, correct: list[str] | None = None, **over: Any
    ) -> dict[str, Any]:
        body = {
            "skill_id": skill, "difficulty": "EASY", "body": "Q?",
            "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}, {"id": "c", "text": "C"}],
            "correct_option_ids": correct or ["a"], **over,
        }
        r = self.req("POST", f"/admin/assessments/{aid}/questions", user, json=body)
        assert r.status_code == 201, r.text
        return dict(r.json())

    def published(self, n_q: int = 2, **over: Any) -> tuple[int, int, list[dict[str, Any]]]:
        _, skill = self.mk_skill(self.admin)
        aid = self.mk_assessment(self.admin, **over)
        qs = [self.add_q(self.admin, aid, skill) for _ in range(n_q)]
        r = self.req("POST", f"/admin/assessments/{aid}/publish", self.admin)
        assert r.status_code == 200, r.text
        return aid, skill, qs


@pytest.fixture
def env(
    client: TestClient, db: Session, auth_headers: Headers, make_user: MakeUser,
    college: College, other_college: College,
) -> Env:
    """Scenario environment."""
    return Env(client, db, auth_headers, make_user, college, other_college)


def _actions(db: Session) -> list[str]:
    return [a for (a,) in db.execute(select(AuditLog.action)).all()]


def _leaks_key(payload: Any) -> bool:
    return "correct_option_ids" in str(payload)


# ---- skills ----------------------------------------------------------------------------------
def test_skill_config_admin_only_and_listing(env: Env) -> None:
    """ADMIN configures skills; FACULTY/STUDENT cannot; any user lists own college."""
    cat, skill = env.mk_skill(env.admin)
    for user in (env.faculty, env.student):
        assert env.req("POST", "/admin/skill-categories", user, json={"name": "X"}).status_code == 403
        assert env.req("POST", "/admin/skills", user,
                       json={"category_id": cat, "name": "Y"}).status_code == 403
        assert env.req("PUT", f"/admin/skills/{skill}", user, json={"name": "Z"}).status_code == 403
        assert env.req("PUT", f"/admin/skill-categories/{cat}", user,
                       json={"name": "Z"}).status_code == 403
    skills = env.req("GET", "/skills", env.student).json()
    assert skills == [{"id": skill, "name": "Python", "description": None,
                       "category_id": cat, "category_name": "Tech"}]
    cats = env.req("GET", "/skill-categories", env.faculty).json()
    assert cats == [{"id": cat, "name": "Tech", "scope": "COMMON", "department_id": None}]
    assert env.client.get(f"{API}/skills").status_code == 401
    assert env.req("GET", "/skills", env.student_b).json() == []
    assert env.req("GET", "/skill-categories", env.admin_b).json() == []


def test_skill_config_validation_and_updates(env: Env, db: Session, college: College) -> None:
    """Duplicates 409, bad references 422, updates work."""
    cat, skill = env.mk_skill(env.admin)
    assert env.req("POST", "/admin/skill-categories", env.admin, json={"name": "Tech"}).status_code == 409
    assert env.req("POST", "/admin/skills", env.admin,
                   json={"category_id": cat, "name": "Python"}).status_code == 409
    assert env.req("POST", "/admin/skills", env.admin,
                   json={"category_id": 999, "name": "N"}).status_code == 422
    assert env.req("POST", "/admin/skill-categories", env.admin,
                   json={"name": "D", "scope": "DEPARTMENT"}).status_code == 422
    assert env.req("POST", "/admin/skill-categories", env.admin,
                   json={"name": "D", "scope": "COMMON", "department_id": 1}).status_code == 422
    dept = Department(college_id=college.id, name="CS", code="CS")
    db.add(dept)
    db.commit()
    r = env.req("POST", "/admin/skill-categories", env.admin,
                json={"name": "D", "scope": "DEPARTMENT", "department_id": dept.id})
    assert r.status_code == 201
    did = r.json()["id"]
    assert env.req("POST", "/admin/skill-categories", env.admin,
                   json={"name": "D2", "scope": "DEPARTMENT", "department_id": 999}).status_code == 422
    u = env.req("PUT", f"/admin/skill-categories/{did}", env.admin, json={"scope": "COMMON"})
    assert u.status_code == 200 and u.json()["department_id"] is None
    assert env.req("PUT", f"/admin/skill-categories/{did}", env.admin,
                   json={"name": "Tech"}).status_code == 409
    u2 = env.req("PUT", f"/admin/skills/{skill}", env.admin,
                 json={"name": "Py3", "description": "d", "category_id": did})
    assert u2.json()["name"] == "Py3" and u2.json()["category_name"] == "D"
    assert env.req("PUT", f"/admin/skills/{skill}", env.admin, json={"category_id": 999}).status_code == 422
    env.mk_skill(env.admin, "Other")
    assert env.req("PUT", f"/admin/skills/{skill}", env.admin, json={"name": "Other"}).status_code == 409
    assert env.req("PUT", "/admin/skills/9999", env.admin, json={"name": "n"}).status_code == 404


def test_skill_cross_college(env: Env) -> None:
    """College B admin cannot see or edit college A skills; cannot use them in questions."""
    cat, skill = env.mk_skill(env.admin)
    assert env.req("PUT", f"/admin/skills/{skill}", env.admin_b, json={"name": "H"}).status_code == 404
    assert env.req("PUT", f"/admin/skill-categories/{cat}", env.admin_b,
                   json={"name": "H"}).status_code == 404
    assert env.req("POST", "/admin/skills", env.admin_b,
                   json={"category_id": cat, "name": "H"}).status_code == 422
    aid_b = env.mk_assessment(env.admin_b)
    r = env.req("POST", f"/admin/assessments/{aid_b}/questions", env.admin_b, json={
        "skill_id": skill, "body": "q", "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
        "correct_option_ids": ["a"]})
    assert r.status_code == 422


# ---- authoring --------------------------------------------------------------------------------
def test_authoring_lifecycle_and_audit(env: Env, db: Session) -> None:
    """Create, update, add questions, publish, archive, version, delete; audited."""
    _, skill = env.mk_skill(env.admin)
    aid = env.mk_assessment(env.faculty, time_limit_min=10, max_attempts=2, negative_marking=0.25)
    detail = env.req("GET", f"/admin/assessments/{aid}", env.faculty).json()
    assert detail["status"] == "DRAFT" and detail["version"] == 1 and detail["questions"] == []
    assert detail["created_by"] == env.faculty.id
    u = env.req("PUT", f"/admin/assessments/{aid}", env.admin,
                json={"title": "New", "time_limit_min": None})
    assert u.json()["title"] == "New" and u.json()["time_limit_min"] is None
    assert u.json()["max_attempts"] == 2
    assert env.req("POST", f"/admin/assessments/{aid}/publish", env.admin).status_code == 422
    q = env.add_q(env.faculty, aid, skill, ["a", "b"], marks=2.5)
    assert q["skill_name"] == "Python" and q["position"] == 0 and q["marks"] == 2.5
    q2 = env.add_q(env.faculty, aid, skill)
    assert q2["position"] == 1
    pub = env.req("POST", f"/admin/assessments/{aid}/publish", env.faculty).json()
    assert pub["status"] == "PUBLISHED" and pub["question_count"] == 2 and pub["total_marks"] == 3.5
    arch = env.req("POST", f"/admin/assessments/{aid}/archive", env.admin)
    assert arch.json()["status"] == "ARCHIVED"
    assert env.req("POST", f"/admin/assessments/{aid}/archive", env.admin).status_code == 409
    d = env.mk_assessment(env.admin)
    assert env.req("DELETE", f"/admin/assessments/{d}", env.admin).status_code == 204
    assert env.req("GET", f"/admin/assessments/{d}", env.admin).status_code == 404
    for action in ["ASSESSMENT_CREATE", "ASSESSMENT_UPDATE", "ASSESSMENT_PUBLISH",
                   "ASSESSMENT_ARCHIVE", "ASSESSMENT_DELETE", "QUESTION_CREATE",
                   "SKILL_CATEGORY_CREATE", "SKILL_CREATE"]:
        assert action in _actions(db), action


def test_admin_listing_filters_and_bank(env: Env) -> None:
    """Status/type/bank filters work and are college scoped."""
    _, skill = env.mk_skill(env.admin)
    _, skill2 = env.mk_skill(env.admin, "SQL")
    a1 = env.mk_assessment(env.admin, type="APTITUDE")
    a2 = env.mk_assessment(env.admin, type="TECHNICAL")
    env.add_q(env.admin, a1, skill, difficulty="EASY")
    env.add_q(env.admin, a2, skill2, difficulty="HARD")
    env.req("POST", f"/admin/assessments/{a1}/publish", env.admin)
    assert [x["id"] for x in env.req("GET", "/admin/assessments?status=PUBLISHED", env.faculty).json()] == [a1]
    assert [x["id"] for x in env.req("GET", "/admin/assessments?type=TECHNICAL", env.faculty).json()] == [a2]
    assert len(env.req("GET", "/admin/question-bank", env.faculty).json()) == 2
    assert len(env.req("GET", f"/admin/question-bank?skill_id={skill2}", env.faculty).json()) == 1
    assert len(env.req("GET", "/admin/question-bank?difficulty=EASY", env.faculty).json()) == 1
    assert len(env.req("GET", f"/admin/question-bank?assessment_id={a2}", env.faculty).json()) == 1
    assert env.req("GET", "/admin/assessments", env.admin_b).json() == []
    assert env.req("GET", "/admin/question-bank", env.admin_b).json() == []


def test_question_validation(env: Env) -> None:
    """Option/answer/skill/marks validation."""
    _, skill = env.mk_skill(env.admin)
    aid = env.mk_assessment(env.admin)
    base: dict[str, Any] = {
        "skill_id": skill, "body": "q",
        "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
        "correct_option_ids": ["a"],
    }

    def post(**over: Any) -> int:
        return int(env.req("POST", f"/admin/assessments/{aid}/questions", env.admin,
                           json={**base, **over}).status_code)

    assert post(options=[{"id": "a", "text": "A"}]) == 422
    assert post(options=[{"id": "a", "text": "A"}, {"id": "a", "text": "B"}]) == 422
    assert post(options=[{"id": " ", "text": "A"}, {"id": "b", "text": "B"}]) == 422
    assert post(correct_option_ids=[]) == 422
    assert post(correct_option_ids=["z"]) == 422
    assert post(skill_id=9999) == 422
    assert post(marks=0) == 422
    assert post(marks=-1) == 422
    assert post(difficulty="IMPOSSIBLE") == 422
    assert post() == 201


def test_question_update_delete_and_draft_only(env: Env) -> None:
    """Questions editable while DRAFT, immutable after publish."""
    _, skill = env.mk_skill(env.admin)
    aid = env.mk_assessment(env.admin)
    q = env.add_q(env.admin, aid, skill)
    r = env.req("PUT", f"/admin/question-bank/{q['id']}", env.admin,
                json={"body": "new", "correct_option_ids": ["b"], "marks": 3, "difficulty": "HARD",
                      "position": 5, "skill_id": skill})
    assert r.status_code == 200
    assert r.json()["body"] == "new" and r.json()["correct_option_ids"] == ["b"]
    assert env.req("PUT", f"/admin/question-bank/{q['id']}", env.admin,
                   json={"correct_option_ids": ["zzz"]}).status_code == 422
    assert env.req("PUT", f"/admin/question-bank/{q['id']}", env.admin,
                   json={"options": [{"id": "a", "text": "A"}]}).status_code == 422
    assert env.req("PUT", f"/admin/question-bank/{q['id']}", env.admin,
                   json={"skill_id": 9999}).status_code == 422
    q2 = env.add_q(env.admin, aid, skill)
    assert env.req("DELETE", f"/admin/question-bank/{q2['id']}", env.admin).status_code == 204
    assert env.req("DELETE", f"/admin/question-bank/{q2['id']}", env.admin).status_code == 404
    env.req("POST", f"/admin/assessments/{aid}/publish", env.admin)
    assert env.req("PUT", f"/admin/question-bank/{q['id']}", env.admin, json={"body": "x"}).status_code == 409
    assert env.req("DELETE", f"/admin/question-bank/{q['id']}", env.admin).status_code == 409
    assert env.req("PUT", f"/admin/assessments/{aid}", env.admin, json={"title": "x"}).status_code == 409
    assert env.req("DELETE", f"/admin/assessments/{aid}", env.admin).status_code == 409
    assert env.req("POST", f"/admin/assessments/{aid}/publish", env.admin).status_code == 409
    r = env.req("POST", f"/admin/assessments/{aid}/questions", env.admin, json={
        "skill_id": skill, "body": "q", "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
        "correct_option_ids": ["a"]})
    assert r.status_code == 409


def test_assessment_input_validation(env: Env) -> None:
    """Bad department and field values are rejected."""
    assert env.req("POST", "/admin/assessments", env.admin,
                   json={"title": "t", "type": "CUSTOM", "department_id": 999}).status_code == 422
    assert env.req("POST", "/admin/assessments", env.admin,
                   json={"title": "t", "type": "NOPE"}).status_code == 422
    assert env.req("POST", "/admin/assessments", env.admin,
                   json={"title": "t", "type": "CUSTOM", "time_limit_min": 0}).status_code == 422
    aid = env.mk_assessment(env.admin)
    assert env.req("PUT", f"/admin/assessments/{aid}", env.admin,
                   json={"department_id": 999}).status_code == 422


def test_versioning_clone(env: Env, db: Session) -> None:
    """new-version clones questions into a DRAFT with version+1 and the same series key."""
    aid, skill, qs = env.published(3)
    assert env.req("POST", f"/admin/assessments/{aid}/new-version", env.admin).status_code == 201
    versions = env.req("GET", "/admin/assessments", env.admin).json()
    new = next(v for v in versions if v["version"] == 2)
    old = next(v for v in versions if v["version"] == 1)
    assert new["status"] == "DRAFT" and new["series_key"] == old["series_key"]
    assert new["id"] != aid and new["question_count"] == 3
    # original untouched; clone editable; third version increments again
    assert old["status"] == "PUBLISHED" and old["question_count"] == 3
    cloned = env.req("GET", f"/admin/assessments/{new['id']}", env.admin).json()["questions"]
    assert {q["id"] for q in cloned}.isdisjoint({q["id"] for q in qs})
    env.req("POST", f"/admin/assessments/{new['id']}/publish", env.admin)
    third = env.req("POST", f"/admin/assessments/{new['id']}/new-version", env.admin).json()
    assert third["version"] == 3
    draft = env.mk_assessment(env.admin)
    assert env.req("POST", f"/admin/assessments/{draft}/new-version", env.admin).status_code == 409
    assert "ASSESSMENT_NEW_VERSION" in _actions(db)


def test_authoring_role_guards(env: Env) -> None:
    """STUDENT cannot author; unauthenticated is 401."""
    _, skill = env.mk_skill(env.admin)
    aid = env.mk_assessment(env.admin)
    for method, path, body in [
        ("GET", "/admin/assessments", None),
        ("POST", "/admin/assessments", {"title": "t", "type": "CUSTOM"}),
        ("GET", f"/admin/assessments/{aid}", None),
        ("PUT", f"/admin/assessments/{aid}", {"title": "t"}),
        ("DELETE", f"/admin/assessments/{aid}", None),
        ("POST", f"/admin/assessments/{aid}/publish", None),
        ("POST", f"/admin/assessments/{aid}/archive", None),
        ("POST", f"/admin/assessments/{aid}/new-version", None),
        ("GET", "/admin/question-bank", None),
        ("POST", f"/admin/assessments/{aid}/questions", {}),
        ("PUT", "/admin/question-bank/1", {}),
        ("DELETE", "/admin/question-bank/1", None),
    ]:
        r = env.req(method, path, env.student, json=body)
        assert r.status_code == 403, (method, path)
        assert env.client.request(method, API + path, json=body).status_code == 401
    assert skill


def test_authoring_cross_college(env: Env) -> None:
    """Admin B cannot touch college A assessments or questions."""
    aid, skill, qs = env.published(1)
    for method, path, body in [
        ("GET", f"/admin/assessments/{aid}", None),
        ("PUT", f"/admin/assessments/{aid}", {"title": "t"}),
        ("DELETE", f"/admin/assessments/{aid}", None),
        ("POST", f"/admin/assessments/{aid}/publish", None),
        ("POST", f"/admin/assessments/{aid}/archive", None),
        ("POST", f"/admin/assessments/{aid}/new-version", None),
        ("POST", f"/admin/assessments/{aid}/questions", {
            "skill_id": skill, "body": "q",
            "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
            "correct_option_ids": ["a"]}),
        ("PUT", f"/admin/question-bank/{qs[0]['id']}", {"body": "x"}),
        ("DELETE", f"/admin/question-bank/{qs[0]['id']}", None),
    ]:
        assert env.req(method, path, env.admin_b, json=body).status_code == 404, (method, path)


def test_delete_blocked_when_attempts_exist(env: Env, db: Session) -> None:
    """A DRAFT with attempts (e.g. forced via DB) cannot be deleted."""
    aid, _, _ = env.published(1)
    stu = db.execute(select(Student)).scalars().first()
    env.req("GET", "/students/me", env.student)
    stu = db.execute(select(Student).where(Student.user_id == env.student.id)).scalar_one()
    db.add(AssessmentAttempt(assessment_id=aid, student_id=stu.id, college_id=stu.college_id,
                             attempt_no=1, started_at=datetime.now(UTC), answers={}))
    db.commit()
    from app.models import Assessment, AssessmentStatus
    a = db.get(Assessment, aid)
    assert a is not None
    a.status = AssessmentStatus.DRAFT
    db.commit()
    assert env.req("DELETE", f"/admin/assessments/{aid}", env.admin).status_code == 409


# ---- student flow ------------------------------------------------------------------------------
def test_student_visibility_and_no_leak(env: Env, db: Session, college: College) -> None:
    """Drafts hidden; department filter; no answer key in any student response."""
    aid, skill, qs = env.published(2)
    draft = env.mk_assessment(env.admin, title="Draft")
    dept1 = Department(college_id=college.id, name="CS", code="CS")
    dept2 = Department(college_id=college.id, name="EE", code="EE")
    db.add_all([dept1, dept2])
    db.commit()
    cs_only = env.mk_assessment(env.admin, title="CS only", department_id=dept1.id)
    env.add_q(env.admin, cs_only, skill)
    env.req("POST", f"/admin/assessments/{cs_only}/publish", env.admin)
    env.req("GET", "/students/me", env.student)
    stu = db.execute(select(Student).where(Student.user_id == env.student.id)).scalar_one()
    stu.department_id = dept2.id
    db.commit()
    listing = env.req("GET", "/assessments", env.student)
    assert [x["id"] for x in listing.json()] == [aid]
    assert listing.json()[0]["attempts_used"] == 0 and listing.json()[0]["in_progress_attempt_id"] is None
    assert env.req("GET", f"/assessments/{draft}", env.student).status_code == 404
    assert env.req("GET", f"/assessments/{cs_only}", env.student).status_code == 404
    assert env.req("POST", f"/assessments/{cs_only}/attempts", env.student).status_code == 404
    assert env.req("POST", f"/assessments/{draft}/attempts", env.student).status_code == 404
    stu.department_id = dept1.id
    db.commit()
    assert {x["id"] for x in env.req("GET", "/assessments", env.student).json()} == {aid, cs_only}
    one = env.req("GET", f"/assessments/{aid}", env.student)
    assert one.status_code == 200 and not _leaks_key(one.json()) and "questions" not in one.json()
    assert not _leaks_key(listing.json())
    att = env.req("POST", f"/assessments/{aid}/attempts", env.student)
    assert att.status_code == 201 and not _leaks_key(att.json())
    body = att.json()
    assert body["questions"][0]["skill_name"] == "Python"
    assert body["questions"][0]["multi_select"] is False
    assert body["expires_at"] is None and body["answers"] == {}
    sub = env.req("POST", f"/attempts/{body['id']}/submit", env.student)
    assert not _leaks_key(sub.json())
    assert not _leaks_key(env.req("GET", f"/attempts/{body['id']}/result", env.student).json())
    assert not _leaks_key(env.req("GET", "/assessments/history", env.student).json())
    assert not _leaks_key(env.req("GET", "/students/me/skills", env.student).json())
    assert qs


def test_staff_cannot_use_student_endpoints(env: Env) -> None:
    """Only STUDENT may take assessments."""
    aid, _, _ = env.published(1)
    for user in (env.admin, env.faculty):
        assert env.req("GET", "/assessments", user).status_code == 403
        assert env.req("POST", f"/assessments/{aid}/attempts", user).status_code == 403
        assert env.req("GET", "/assessments/history", user).status_code == 403
        assert env.req("GET", "/students/me/skills", user).status_code == 403
    assert env.client.get(f"{API}/assessments").status_code == 401


def test_attempt_lifecycle_scoring_and_student_skills(env: Env, db: Session) -> None:
    """Full flow: start, save, resume, submit, result, history, StudentSkill upsert."""
    _, skill = env.mk_skill(env.admin)
    _, skill2 = env.mk_skill(env.admin, "SQL", "Data")
    aid = env.mk_assessment(env.admin, negative_marking=0.5)
    q1 = env.add_q(env.admin, aid, skill, ["a"], marks=2)
    q2 = env.add_q(env.admin, aid, skill, ["a", "b"], marks=2)
    q3 = env.add_q(env.admin, aid, skill2, ["c"], marks=1)
    env.add_q(env.admin, aid, skill2, ["c"], marks=1)
    env.req("POST", f"/admin/assessments/{aid}/publish", env.admin)

    att = env.req("POST", f"/assessments/{aid}/attempts", env.student)
    assert att.status_code == 201 and att.json()["attempt_no"] == 1
    multi = {q["id"]: q["multi_select"] for q in att.json()["questions"]}
    assert multi[q1["id"]] is False and multi[q2["id"]] is True
    att_id = att.json()["id"]
    resume = env.req("POST", f"/assessments/{aid}/attempts", env.student)
    assert resume.status_code == 200 and resume.json()["id"] == att_id
    listing = env.req("GET", "/assessments", env.student).json()[0]
    assert listing["attempts_used"] == 1 and listing["in_progress_attempt_id"] == att_id

    saved = env.req("PUT", f"/attempts/{att_id}/answers", env.student, json={
        "answers": {str(q1["id"]): ["a"], str(q2["id"]): ["a"]}})
    assert saved.json() == {"saved": 2}
    env.req("PUT", f"/attempts/{att_id}/answers", env.student,
            json={"answers": {str(q3["id"]): ["a"]}})
    resumed = env.req("POST", f"/assessments/{aid}/attempts", env.student).json()
    assert resumed["answers"] == {str(q1["id"]): ["a"], str(q2["id"]): ["a"], str(q3["id"]): ["a"]}
    assert env.req("GET", f"/attempts/{att_id}/result", env.student).status_code == 404

    res = env.req("POST", f"/attempts/{att_id}/submit", env.student)
    assert res.status_code == 200
    r = res.json()
    # q1 +2, q2 partial -> -1, q3 wrong -> -0.5, q4 unanswered 0. total 0.5 of 6
    assert r["total_score"] == 0.5 and r["max_score"] == 6 and r["percentage"] == 8.33
    by_skill = {s["skill_id"]: s for s in r["per_skill_scores"]}
    assert by_skill[skill]["score"] == 1 and by_skill[skill]["percentage"] == 25
    assert by_skill[skill2]["score"] == 0 and by_skill[skill2]["skill_name"] == "SQL"
    assert r["assessment_title"] == "Quiz" and r["assessment_version"] == 1
    again = env.req("POST", f"/attempts/{att_id}/submit", env.student).json()
    assert again["id"] == r["id"] and again["total_score"] == r["total_score"]
    assert env.req("GET", f"/attempts/{att_id}/result", env.student).json()["id"] == r["id"]
    assert env.req("PUT", f"/attempts/{att_id}/answers", env.student,
                   json={"answers": {}}).status_code == 409

    skills = {s["skill_id"]: s for s in env.req("GET", "/students/me/skills", env.student).json()}
    assert skills[skill]["score"] == 25 and skills[skill]["evidence_count"] == 2
    assert skills[skill]["confidence"] is None and skills[skill]["category_name"] == "Tech"
    assert skills[skill2]["score"] == 0 and skills[skill2]["evidence_count"] == 2

    # second attempt: perfect on skill 1 -> latest wins, evidence accumulates
    att2 = env.req("POST", f"/assessments/{aid}/attempts", env.student).json()
    assert att2["attempt_no"] == 2
    env.req("PUT", f"/attempts/{att2['id']}/answers", env.student,
            json={"answers": {str(q1["id"]): ["a"], str(q2["id"]): ["b", "a"]}})
    env.req("POST", f"/attempts/{att2['id']}/submit", env.student)
    skills = {s["skill_id"]: s for s in env.req("GET", "/students/me/skills", env.student).json()}
    assert skills[skill]["score"] == 100 and skills[skill]["evidence_count"] == 4
    row = db.execute(select(StudentSkill).where(StudentSkill.skill_id == skill)).scalar_one()
    assert row.last_result_id is not None and row.confidence is None
    hist = env.req("GET", "/assessments/history", env.student).json()
    assert [h["attempt_no"] for h in hist] == [2, 1]
    assert hist[0]["submitted_at"] is not None and hist[0]["assessment_title"] == "Quiz"
    assert env.req("GET", "/assessments/history", env.student2).json() == []
    assert {"ASSESSMENT_ATTEMPT_START", "ASSESSMENT_SUBMIT"} <= set(_actions(db))


def test_max_attempts(env: Env) -> None:
    """Exceeding max_attempts yields 409."""
    aid, _, _ = env.published(1, max_attempts=1)
    a1 = env.req("POST", f"/assessments/{aid}/attempts", env.student).json()
    env.req("POST", f"/attempts/{a1['id']}/submit", env.student)
    r = env.req("POST", f"/assessments/{aid}/attempts", env.student)
    assert r.status_code == 409 and r.json() == {"detail": "Maximum attempts reached"}
    # other students are unaffected
    assert env.req("POST", f"/assessments/{aid}/attempts", env.student2).status_code == 201


def test_answer_validation(env: Env) -> None:
    """Unknown question/option ids are 422; clearing an answer is allowed."""
    aid, _, qs = env.published(1)
    att = env.req("POST", f"/assessments/{aid}/attempts", env.student).json()
    path = f"/attempts/{att['id']}/answers"
    qid = str(qs[0]["id"])
    assert env.req("PUT", path, env.student, json={"answers": {"99999": ["a"]}}).status_code == 422
    assert env.req("PUT", path, env.student, json={"answers": {"abc": ["a"]}}).status_code == 422
    assert env.req("PUT", path, env.student, json={"answers": {qid: ["zzz"]}}).status_code == 422
    assert env.req("PUT", path, env.student, json={"answers": {qid: ["a", "a"]}}).json() == {"saved": 1}
    assert env.req("PUT", path, env.student, json={"answers": {qid: []}}).json() == {"saved": 1}
    assert env.req("POST", f"/assessments/{aid}/attempts", env.student).json()["answers"] == {qid: []}


def _age_attempt(db: Session, attempt_id: int, minutes: int) -> None:
    att = db.get(AssessmentAttempt, attempt_id)
    assert att is not None
    att.started_at = datetime.now(UTC) - timedelta(minutes=minutes)
    db.commit()


def test_time_limit_and_expiry(env: Env, db: Session) -> None:
    """Past the deadline: no new answers, submit scores saved answers as EXPIRED."""
    aid, _, qs = env.published(2, time_limit_min=10)
    att = env.req("POST", f"/assessments/{aid}/attempts", env.student).json()
    assert att["expires_at"] is not None
    start = datetime.fromisoformat(att["started_at"])
    assert datetime.fromisoformat(att["expires_at"]) - start == timedelta(minutes=10)
    env.req("PUT", f"/attempts/{att['id']}/answers", env.student,
            json={"answers": {str(qs[0]["id"]): ["a"]}})
    _age_attempt(db, att["id"], 11)
    assert env.req("PUT", f"/attempts/{att['id']}/answers", env.student,
                   json={"answers": {str(qs[1]["id"]): ["a"]}}).status_code == 409
    res = env.req("POST", f"/attempts/{att['id']}/submit", env.student)
    assert res.status_code == 200 and res.json()["total_score"] == 1
    assert db.get(AssessmentAttempt, att["id"]).status.value == "EXPIRED"  # type: ignore[union-attr]
    assert env.req("POST", f"/attempts/{att['id']}/submit", env.student).json()["id"] == res.json()["id"]


def test_stale_attempt_is_finalised_on_restart(env: Env, db: Session) -> None:
    """An expired IN_PROGRESS attempt is closed and counted before a new one starts."""
    aid, _, _ = env.published(1, time_limit_min=5, max_attempts=2)
    a1 = env.req("POST", f"/assessments/{aid}/attempts", env.student).json()
    _age_attempt(db, a1["id"], 30)
    assert env.req("GET", "/assessments", env.student).json()[0]["in_progress_attempt_id"] is None
    a2 = env.req("POST", f"/assessments/{aid}/attempts", env.student)
    assert a2.status_code == 201 and a2.json()["attempt_no"] == 2
    assert db.get(AssessmentAttempt, a1["id"]).status.value == "EXPIRED"  # type: ignore[union-attr]
    _age_attempt(db, a2.json()["id"], 30)
    assert env.req("POST", f"/assessments/{aid}/attempts", env.student).status_code == 409


def test_published_content_immutable_for_running_attempts(env: Env) -> None:
    """Archiving does not break an in-progress attempt; new attempts are hidden."""
    aid, _, _ = env.published(1)
    att = env.req("POST", f"/assessments/{aid}/attempts", env.student).json()
    env.req("POST", f"/admin/assessments/{aid}/archive", env.admin)
    assert env.req("GET", "/assessments", env.student2).json() == []
    assert env.req("POST", f"/assessments/{aid}/attempts", env.student2).status_code == 404
    assert env.req("POST", f"/attempts/{att['id']}/submit", env.student).status_code == 200


def test_attempt_ownership_and_cross_college(env: Env) -> None:
    """Other students and other colleges get 404 on every attempt endpoint."""
    aid, _, qs = env.published(1)
    att = env.req("POST", f"/assessments/{aid}/attempts", env.student).json()
    env.req("POST", f"/attempts/{att['id']}/submit", env.student)
    live = env.req("POST", f"/assessments/{aid}/attempts", env.student).json()
    for other in (env.student2, env.student_b):
        assert env.req("PUT", f"/attempts/{live['id']}/answers", other,
                       json={"answers": {}}).status_code == 404
        assert env.req("POST", f"/attempts/{live['id']}/submit", other).status_code == 404
        assert env.req("GET", f"/attempts/{att['id']}/result", other).status_code == 404
    # college B student cannot see or start college A assessments
    assert env.req("GET", "/assessments", env.student_b).json() == []
    assert env.req("GET", f"/assessments/{aid}", env.student_b).status_code == 404
    assert env.req("POST", f"/assessments/{aid}/attempts", env.student_b).status_code == 404
    assert env.req("GET", "/assessments/history", env.student_b).json() == []
    assert env.req("GET", "/students/me/skills", env.student_b).json() == []
    assert qs


def test_college_b_has_isolated_flow(env: Env) -> None:
    """College B can run its own assessment without touching college A data."""
    aid, _, _ = env.published(1)
    _, skill_b = env.mk_skill(env.admin_b, "Python")
    bid = env.mk_assessment(env.admin_b)
    env.add_q(env.admin_b, bid, skill_b)
    env.req("POST", f"/admin/assessments/{bid}/publish", env.admin_b)
    assert [x["id"] for x in env.req("GET", "/assessments", env.student_b).json()] == [bid]
    att = env.req("POST", f"/assessments/{bid}/attempts", env.student_b)
    assert att.status_code == 201
    assert [x["id"] for x in env.req("GET", "/assessments", env.student).json()] == [aid]
