"""The starter pack: its data is internally consistent and loading it through the API works."""
import json
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import College, Department, User, UserRole
from scripts import load_starter_pack as loader

PACK_PATH = loader.DEFAULT_PACK


def pack() -> dict[str, Any]:
    return json.loads(PACK_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


class InProcessClient:
    """Same interface as loader.Client, but talks to the FastAPI app in-process."""

    def __init__(self, http: TestClient, headers: dict[str, str]) -> None:
        self.http = http
        self.headers = headers

    def call(self, method: str, path: str, body: Any = None) -> Any:
        res = self.http.request(method, "/api/v1" + path, json=body, headers=self.headers)
        if res.status_code >= 400:
            raise loader.ApiError(f"{method} {path} -> {res.status_code}: {res.text[:200]}")
        return res.json() if res.content else None


def test_pack_is_internally_consistent() -> None:
    data = pack()
    skills = {s for c in data["categories"] for s in c["skills"]}
    assert len(skills) == sum(len(c["skills"]) for c in data["categories"]), "duplicate skill names"
    asked = set()
    for a in data["assessments"]:
        for q in a["questions"]:
            assert q["skill"] in skills
            assert len(q["options"]) >= 2 and q["correct"], q["body"]
            assert set(q["correct"]) <= {o["id"] for o in q["options"]}, q["body"]
            asked.add(q["skill"])
    for role in data["roles"]:
        for skill, level, weight in role["skills"]:
            assert skill in skills and 0 <= level <= 100 and weight > 0
            assert skill in asked, f"{role['name']} requires {skill}, which has no questions"
    assert set(data["readiness_rule"]["weights"]) == {c["name"] for c in data["categories"]}
    assert data["readiness_rule"]["levels"][0][1] == 0, "one level must start at 0"
    assert all(skill in skills for skill, *_ in data["resources"])
    assert all(url.startswith("https://") for _, _, url in data["resources"])


def test_pack_marks_itself_as_placeholder_and_keeps_sample_job_hidden() -> None:
    data = pack()
    assert "placeholder" in data["notice"].lower()
    assert "sample" in data["sample_job"]["title"].lower()
    assert "sample" in data["sample_company"]["name"].lower()


@pytest.fixture
def admin_client(
    client: TestClient,
    db: Session,
    college: College,
    make_user: Callable[..., User],
    auth_headers: Callable[[User], dict[str, str]],
) -> InProcessClient:
    for code, name in (("CSE", "Computer Science"), ("IT", "Information Technology")):
        db.add(Department(college_id=college.id, name=name, code=code))
    db.commit()
    admin = make_user(college, UserRole.ADMIN, "admin@a.com")
    return InProcessClient(client, auth_headers(admin))


def test_load_creates_everything_and_is_idempotent(admin_client: InProcessClient) -> None:
    data = pack()
    made = loader.load(admin_client, data)  # type: ignore[arg-type]
    assert made["skill categories"] == len(data["categories"])
    assert made["skills"] == sum(len(c["skills"]) for c in data["categories"])
    assert made["career roles"] == len(data["roles"])
    assert made["readiness rule"] == 1
    assert made["assessments (published)"] == len(data["assessments"])
    assert made["learning resources (approved)"] == len(data["resources"])
    assert made["interview questions"] == len(data["interview_questions"])

    rules = admin_client.call("GET", "/admin/readiness-rules")
    assert [r["is_active"] for r in rules] == [True]
    assessments = admin_client.call("GET", "/admin/assessments")
    assert {a["status"] for a in assessments} == {"PUBLISHED"}
    assert sum(a["question_count"] for a in assessments) == sum(len(a["questions"]) for a in data["assessments"])
    assert all(r["is_approved"] for r in admin_client.call("GET", "/admin/learning-resources"))
    jobs = admin_client.call("GET", "/admin/jobs")
    assert [(j["title"], j["status"], j["has_eligibility_rule"]) for j in jobs] == [
        (data["sample_job"]["title"], "DRAFT", True)
    ]

    assert loader.load(admin_client, data) == {}, "a second run must create nothing"  # type: ignore[arg-type]
    assert len(admin_client.call("GET", "/admin/career-roles")) == len(data["roles"])


def test_students_see_the_assessments_but_not_the_draft_job(
    admin_client: InProcessClient,
    client: TestClient,
    college: College,
    db: Session,
    make_user: Callable[..., User],
    auth_headers: Callable[[User], dict[str, str]],
) -> None:
    loader.load(admin_client, pack())  # type: ignore[arg-type]
    student = make_user(college, UserRole.STUDENT, "s@a.com")
    headers = auth_headers(student)
    titles = {a["title"] for a in client.get("/api/v1/assessments", headers=headers).json()}
    assert titles == {a["title"] for a in pack()["assessments"]}
    assert client.get("/api/v1/jobs", headers=headers).json() == []
    assert db.execute(select(User).where(User.id == student.id)).scalar_one()
