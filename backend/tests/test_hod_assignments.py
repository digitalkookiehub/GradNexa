"""Admin HOD-assignment CRUD tests."""
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, College, HodAssignment, User, UserRole
from tests.test_hod_dashboard import World

Headers = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]
URL = "/api/v1/admin/hod-assignments"


@pytest.fixture
def world(
    db: Session, college: College, other_college: College, make_user: MakeUser
) -> World:
    return World(db, make_user, college, other_college)


def test_crud_flow(
    world: World, client: TestClient, auth_headers: Headers, db: Session
) -> None:
    h = auth_headers(world.admin)
    assert client.get(URL, headers=h).json() == []
    r = client.post(
        URL, headers=h, json={"hod_user_id": world.hod.id, "department_id": world.cs.id}
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["hod_user_id"] == world.hod.id
    assert body["hod_name"] == world.hod.full_name
    assert body["hod_email"] == world.hod.email
    assert body["department_id"] == world.cs.id
    assert body["department_name"] == "Computer Science"
    listed = client.get(URL, headers=h).json()
    assert listed == [body]
    assert client.delete(f"{URL}/{body['id']}", headers=h).status_code == 204
    assert client.get(URL, headers=h).json() == []
    actions = {
        a.action for a in db.execute(select(AuditLog)).scalars()
        if a.action.startswith("HOD_ASSIGNMENT")
    }
    assert actions == {"HOD_ASSIGNMENT_CREATE", "HOD_ASSIGNMENT_DELETE"}


def test_validation(world: World, client: TestClient, auth_headers: Headers) -> None:
    h = auth_headers(world.admin)
    payload = {"hod_user_id": world.hod.id, "department_id": world.cs.id}
    assert client.post(URL, headers=h, json=payload).status_code == 201
    dup = client.post(URL, headers=h, json=payload)
    assert dup.status_code == 409
    assert "detail" in dup.json()
    # non-HOD user
    r = client.post(URL, headers=h, json={"hod_user_id": world.tpo.id, "department_id": world.cs.id})
    assert r.status_code == 404
    # unknown user / department
    assert client.post(
        URL, headers=h, json={"hod_user_id": 99999, "department_id": world.cs.id}
    ).status_code == 404
    assert client.post(
        URL, headers=h, json={"hod_user_id": world.hod.id, "department_id": 99999}
    ).status_code == 404
    # other college's department / HOD
    foreign = world.dept(world.b, "FF", "Foreign")
    assert client.post(
        URL, headers=h, json={"hod_user_id": world.hod.id, "department_id": foreign.id}
    ).status_code == 404
    assert client.post(
        URL, headers=h, json={"hod_user_id": world.hod_b.id, "department_id": world.cs.id}
    ).status_code == 404
    # malformed body
    assert client.post(URL, headers=h, json={"hod_user_id": world.hod.id}).status_code == 422


def test_delete_missing_and_cross_college(
    world: World, client: TestClient, auth_headers: Headers, db: Session
) -> None:
    assert client.delete(f"{URL}/999", headers=auth_headers(world.admin)).status_code == 404
    world.assign_hod(world.hod, world.cs)
    row = db.execute(select(HodAssignment)).scalars().one()
    assert client.delete(f"{URL}/{row.id}", headers=auth_headers(world.admin_b)).status_code == 404
    assert client.get(URL, headers=auth_headers(world.admin_b)).json() == []
    assert len(client.get(URL, headers=auth_headers(world.admin)).json()) == 1


@pytest.mark.parametrize(
    "role",
    [UserRole.TPO, UserRole.HOD, UserRole.FACULTY, UserRole.STUDENT, UserRole.SUPER_ADMIN],
)
def test_role_guards(
    world: World, client: TestClient, auth_headers: Headers, make_user: MakeUser,
    role: UserRole,
) -> None:
    user = make_user(world.a, role, email=f"g-{role.value}@x.test")
    h = auth_headers(user)
    assert client.get(URL, headers=h).status_code == 403
    assert client.post(
        URL, headers=h, json={"hod_user_id": world.hod.id, "department_id": world.cs.id}
    ).status_code == 403
    assert client.delete(f"{URL}/1", headers=h).status_code == 403
    assert client.get(URL).status_code == 401
