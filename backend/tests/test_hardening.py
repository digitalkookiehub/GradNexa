"""Phase 16 hardening: production config guard, security headers, token abuse, hashing cost."""
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.auth.security import create_access_token, hash_password
from app.config import Settings
from app.models import College

GOOD_KEY = "k" * 40


def prod(**over: Any) -> Settings:
    """Build production settings without reading any .env file."""
    values: dict[str, Any] = {
        "DATABASE_URL": "postgresql://u:p@localhost/db",
        "SECRET_KEY": GOOD_KEY,
        "ENVIRONMENT": "production",
        "RATE_LIMIT_ENABLED": True,
        "BCRYPT_ROUNDS": 12,
        "CORS_ORIGINS": "https://app.example.com",
    }
    values.update(over)
    return Settings(_env_file=None, **values)


def test_production_accepts_safe_config() -> None:
    assert prod().ENVIRONMENT == "production"


@pytest.mark.parametrize(
    "override",
    [
        {"SECRET_KEY": "short"},
        {"SECRET_KEY": "please-change-this-secret-in-production-1234"},
        {"RATE_LIMIT_ENABLED": False},
        {"BCRYPT_ROUNDS": 4},
        {"CORS_ORIGINS": "https://a.example.com,*"},
    ],
)
def test_production_rejects_unsafe_config(override: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        prod(**override)


def test_development_allows_weak_config() -> None:
    cfg = prod(ENVIRONMENT="development", SECRET_KEY="short", RATE_LIMIT_ENABLED=False, BCRYPT_ROUNDS=4)
    assert cfg.SECRET_KEY == "short"


def test_security_headers_present(client: TestClient) -> None:
    res = client.get("/health")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert res.headers["referrer-policy"] == "no-referrer"
    assert res.headers["cache-control"] == "no-store"


def test_security_headers_on_error_responses(client: TestClient) -> None:
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert res.headers["x-content-type-options"] == "nosniff"


def test_token_signed_with_other_key_rejected(client: TestClient, college: College) -> None:
    import jwt

    forged = jwt.encode(
        {"sub": "1", "type": "access", "role": "ADMIN", "college_id": str(college.id), "exp": 9999999999},
        "some-other-secret-key-of-sufficient-length",
        algorithm="HS256",
    )
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert res.status_code == 401


def test_alg_none_token_rejected(client: TestClient) -> None:
    import jwt

    unsigned = jwt.encode({"sub": "1", "type": "access", "role": "ADMIN", "exp": 9999999999}, None, algorithm="none")
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {unsigned}"})
    assert res.status_code == 401


def test_expired_token_rejected(client: TestClient, college: College) -> None:
    import jwt

    from app.config import settings

    expired = jwt.encode(
        {"sub": "1", "type": "access", "role": "STUDENT", "college_id": str(college.id), "exp": 1},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert res.status_code == 401


def test_token_for_unknown_user_rejected(client: TestClient, college: College) -> None:
    token = create_access_token(999999, "ADMIN", college.id)
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


def test_role_claim_in_token_cannot_escalate(
    client: TestClient, college: College, make_user: Any
) -> None:
    """A student's token that claims ADMIN must not unlock admin routes (role comes from the DB)."""
    from app.models import UserRole

    student = make_user(college, UserRole.STUDENT)
    token = create_access_token(student.id, "ADMIN", college.id)
    res = client.get("/api/v1/admin/assessments", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


def test_tenant_claim_in_token_cannot_switch_college(
    client: TestClient, college: College, other_college: College, make_user: Any
) -> None:
    """A token claiming another college must not expose that college's data."""
    from app.models import UserRole

    admin_b = make_user(other_college, UserRole.ADMIN)
    admin_a = make_user(college, UserRole.ADMIN)
    token = create_access_token(admin_a.id, "ADMIN", other_college.id)
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    # Either rejected outright or served from the user's real college - never college B.
    if res.status_code == 200:
        assert res.json().get("college_id") in (None, college.id, str(college.id))
        assert res.json().get("email") != admin_b.email


def test_bcrypt_cost_is_configurable() -> None:
    assert hash_password("Password123!").startswith("$2b$04$")


def test_hash_password_is_fast_in_tests() -> None:
    start = time.perf_counter()
    for _ in range(5):
        hash_password("Password123!")
    assert time.perf_counter() - start < 2.0


def test_docs_do_not_expose_secrets(client: TestClient) -> None:
    from app.config import settings

    res = client.get("/openapi.json")
    assert res.status_code == 200
    assert settings.SECRET_KEY not in res.text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("http://a.com,http://b.com", ["http://a.com", "http://b.com"]),
        (" http://a.com , ", ["http://a.com"]),
        ('["http://a.com", "http://b.com"]', ["http://a.com", "http://b.com"]),
    ],
)
def test_cors_origins_parse_from_environment(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: list[str]
) -> None:
    """Regression: a comma-separated CORS_ORIGINS in the real environment used to crash startup."""
    monkeypatch.setenv("CORS_ORIGINS", raw)
    cfg = Settings(_env_file=None, DATABASE_URL="postgresql://u:p@localhost/db", SECRET_KEY="x")  # type: ignore[call-arg]
    assert cfg.cors_origins_list == expected
