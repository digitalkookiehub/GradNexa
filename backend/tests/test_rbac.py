"""RBAC and tenant isolation tests."""
from collections.abc import Callable

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import TenantContext, get_db, get_tenant, require_role, scope_to_college
from app.main import app
from app.models import College, User, UserRole

probe = APIRouter(prefix="/_probe")


@probe.get("/staff")
async def staff_only(
    user: User = Depends(require_role(UserRole.TPO, UserRole.ADMIN)),
) -> dict[str, str]:
    """Probe endpoint restricted to TPO/ADMIN."""
    return {"role": user.role.value}


@probe.get("/colleagues")
async def colleagues(
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> dict[str, list[str]]:
    """Probe endpoint returning only same-college emails."""
    stmt = scope_to_college(select(User.email), User, tenant.college_id)
    return {"emails": list(db.execute(stmt).scalars())}


app.include_router(probe)


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (UserRole.STUDENT, 403),
        (UserRole.FACULTY, 403),
        (UserRole.HOD, 403),
        (UserRole.SUPER_ADMIN, 403),
        (UserRole.TPO, 200),
        (UserRole.ADMIN, 200),
    ],
)
def test_role_guard(
    client: TestClient,
    users: dict[UserRole, User],
    auth_headers: Callable[[User], dict[str, str]],
    role: UserRole,
    expected: int,
) -> None:
    """Only listed roles pass the guard; others get 403."""
    response = client.get("/_probe/staff", headers=auth_headers(users[role]))
    assert response.status_code == expected
    if expected == 403:
        assert response.json() == {"detail": "Insufficient permissions"}


def test_role_guard_unauthenticated(client: TestClient) -> None:
    """No token gives 401."""
    assert client.get("/_probe/staff").status_code == 401


def test_invalid_token(client: TestClient) -> None:
    """Garbage token gives 401."""
    response = client.get("/_probe/staff", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


def test_refresh_token_not_accepted_as_access(client: TestClient, college: College) -> None:
    """A refresh token cannot be used as an access token."""
    from app.auth.security import create_refresh_token

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {create_refresh_token(1)}"}
    )
    assert response.status_code == 401


def test_cross_college_isolation(
    client: TestClient,
    college: College,
    other_college: College,
    make_user: Callable[..., User],
    auth_headers: Callable[[User], dict[str, str]],
) -> None:
    """Tenant-scoped queries never expose another college's users."""
    a = make_user(college, UserRole.STUDENT, "a@example.com")
    make_user(other_college, UserRole.STUDENT, "b@example.com")
    response = client.get("/_probe/colleagues", headers=auth_headers(a))
    assert response.status_code == 200
    assert response.json()["emails"] == ["a@example.com"]


def test_inactive_user_rejected(
    client: TestClient,
    db: Session,
    users: dict[UserRole, User],
    auth_headers: Callable[[User], dict[str, str]],
) -> None:
    """Deactivated users are rejected even with a valid token."""
    user = users[UserRole.STUDENT]
    headers = auth_headers(user)
    user.is_active = False
    db.commit()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
