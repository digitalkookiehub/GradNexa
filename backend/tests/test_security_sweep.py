"""Phase 16 sweep: every API route is authenticated, and /admin routes reject non-staff roles.

The sweep is generated from the live route table, so a new endpoint added without an auth
dependency fails this test instead of silently shipping open.
"""
import re
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import User, UserRole

API_PREFIX = "/api/v1"

# Endpoints that are intentionally reachable without a token.
PUBLIC = {
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/refresh"),
    ("POST", "/api/v1/auth/logout"),
    ("POST", "/api/v1/auth/forgot-password"),
    ("POST", "/api/v1/auth/reset-password"),
}

# Roles that may use /admin routes (each route may be narrower; the rest must always be 403).
STAFF_ROLES = {UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.TPO, UserRole.FACULTY, UserRole.HOD}


def _routes() -> list[tuple[str, str]]:
    """Every (method, path) under /api/v1, read from the OpenAPI schema.

    The schema is used instead of app.routes because newer FastAPI versions keep routers as lazy
    wrappers there; the schema lists every operation the same way on every version.
    """
    found: list[tuple[str, str]] = []
    for path, operations in app.openapi()["paths"].items():
        if not path.startswith(API_PREFIX):
            continue
        for method in sorted(operations):
            if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                found.append((method.upper(), path))
    return found


def _concrete(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "1", path)


ROUTES = _routes()
PROTECTED = [(m, p) for m, p in ROUTES if (m, p) not in PUBLIC and not p.startswith(f"{API_PREFIX}/health")]
ADMIN_ROUTES = [(m, p) for m, p in PROTECTED if p.startswith(f"{API_PREFIX}/admin")]


def test_route_table_is_not_empty() -> None:
    """Guard against the sweep silently testing nothing."""
    assert len(PROTECTED) > 100
    assert len(ADMIN_ROUTES) > 30


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_route_requires_authentication(client: TestClient, method: str, path: str) -> None:
    """No token -> 401 on every non-public route."""
    response = client.request(method, _concrete(path))
    assert response.status_code == 401, f"{method} {path} -> {response.status_code}"


@pytest.mark.parametrize(("method", "path"), PROTECTED[:40])
def test_garbage_token_rejected(client: TestClient, method: str, path: str) -> None:
    """A malformed bearer token is rejected, never treated as anonymous access."""
    response = client.request(method, _concrete(path), headers={"Authorization": "Bearer not.a.jwt"})
    assert response.status_code == 401, f"{method} {path} -> {response.status_code}"


@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_student_cannot_reach_admin_routes(
    client: TestClient,
    users: dict[UserRole, User],
    auth_headers: Callable[[User], dict[str, str]],
    method: str,
    path: str,
) -> None:
    """Students get 403 on every /admin route."""
    response = client.request(method, _concrete(path), headers=auth_headers(users[UserRole.STUDENT]))
    assert response.status_code == 403, f"{method} {path} -> {response.status_code}"
