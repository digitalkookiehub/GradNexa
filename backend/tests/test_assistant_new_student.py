"""Regression: a brand-new student (no Student row yet) can use the assistant and MCP tools.

Found during a live run: the assistant answered 404 "Student profile not found" for a student who
had registered but not yet opened any endpoint that lazily creates their Student row.
"""
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import College, Student, User, UserRole


def test_assistant_works_for_student_without_student_row(
    client: TestClient,
    db: Session,
    college: College,
    make_user: Callable[..., User],
    auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(college, UserRole.STUDENT)
    assert db.execute(select(Student).where(Student.user_id == user.id)).scalar_one_or_none() is None

    res = client.post(
        "/api/v1/assistant/query",
        json={"question": "What is a left join?"},
        headers=auth_headers(user),
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["llm_used"] is False
    # The row is created lazily, exactly like /students/me and /dashboard/student.
    created = db.execute(select(Student).where(Student.user_id == user.id)).scalar_one_or_none()
    assert created is not None
    assert created.college_id == college.id


def test_mcp_student_tool_works_for_student_without_student_row(
    client: TestClient,
    db: Session,
    college: College,
    make_user: Callable[..., User],
    auth_headers: Callable[[User], dict[str, str]],
) -> None:
    user = make_user(college, UserRole.STUDENT)

    res = client.post(
        "/api/v1/mcp/tools/get_student_profile/call",
        json={"arguments": {}},
        headers=auth_headers(user),
    )

    assert res.status_code == 200, res.text
    assert res.json()["tool"] == "get_student_profile"
