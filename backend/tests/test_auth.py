"""Authentication endpoint tests."""
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import verify_password
from app.config import settings
from app.dependencies import limiter
from app.models import (
    AuditLog,
    College,
    PasswordResetToken,
    RefreshToken,
    User,
    UserRole,
)
from app.services import email_service
from tests.conftest import PASSWORD

API = "/api/v1/auth"


def _register(client: TestClient, email: str = "new@example.com", code: str = "COLA") -> object:
    return client.post(
        f"{API}/register",
        json={"email": email, "password": PASSWORD, "full_name": "New User", "college_code": code},
    )


def _login(client: TestClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    response = client.post(f"{API}/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()


def _actions(db: Session) -> list[str]:
    return list(db.execute(select(AuditLog.action)).scalars())


def test_register_creates_student(client: TestClient, college: College, db: Session) -> None:
    """Register returns 201, STUDENT role, and never leaks password data."""
    response = _register(client)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {
        "id", "email", "full_name", "role", "college_id", "is_active", "is_verified"
    }
    assert body["role"] == "STUDENT"
    assert body["college_id"] == college.id
    assert "password" not in response.text
    assert "hashed_password" not in response.text
    assert "REGISTER" in _actions(db)


def test_register_ignores_role_escalation(client: TestClient, college: College) -> None:
    """Extra role field in the payload cannot escalate privileges."""
    response = client.post(
        f"{API}/register",
        json={
            "email": "evil@example.com",
            "password": PASSWORD,
            "full_name": "Evil",
            "college_code": "COLA",
            "role": "SUPER_ADMIN",
        },
    )
    assert response.status_code == 201
    assert response.json()["role"] == "STUDENT"


def test_register_duplicate_email(client: TestClient, college: College) -> None:
    """Duplicate email gives 409 (case-insensitive)."""
    assert _register(client).status_code == 201
    response = _register(client, email="NEW@example.com")
    assert response.status_code == 409
    assert "detail" in response.json()


def test_register_unknown_college(client: TestClient) -> None:
    """Unknown college code gives 404."""
    assert _register(client, code="NOPE").status_code == 404


def test_register_short_password(client: TestClient, college: College) -> None:
    """Password under 8 chars is rejected with 422 and a detail string."""
    response = client.post(
        f"{API}/register",
        json={
            "email": "a@example.com", "password": "short", "full_name": "A",
            "college_code": "COLA",
        },
    )
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_password_stored_as_bcrypt(client: TestClient, college: College, db: Session) -> None:
    """Stored password is a bcrypt hash, not plaintext."""
    _register(client)
    user = db.execute(select(User).where(User.email == "new@example.com")).scalar_one()
    assert user.hashed_password != PASSWORD
    assert user.hashed_password.startswith("$2")
    assert verify_password(PASSWORD, user.hashed_password)


def test_login_success(
    client: TestClient, users: dict[UserRole, User], db: Session
) -> None:
    """Login returns a bearer token pair and stores only the refresh hash."""
    user = users[UserRole.STUDENT]
    tokens = _login(client, user.email)
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] and tokens["refresh_token"]
    stored = db.execute(select(RefreshToken.token_hash)).scalars().all()
    assert len(stored) == 1
    assert tokens["refresh_token"] not in stored
    assert "LOGIN" in _actions(db)


def test_login_failures(
    client: TestClient, users: dict[UserRole, User], db: Session
) -> None:
    """Wrong password and unknown email both give 401 and audit LOGIN_FAILED."""
    user = users[UserRole.STUDENT]
    bad_pw = client.post(f"{API}/login", json={"email": user.email, "password": "wrong-password"})
    unknown = client.post(f"{API}/login", json={"email": "no@example.com", "password": PASSWORD})
    assert bad_pw.status_code == 401
    assert unknown.status_code == 401
    assert bad_pw.json() == unknown.json()
    assert _actions(db).count("LOGIN_FAILED") == 2


def test_login_inactive_user(
    client: TestClient, users: dict[UserRole, User], db: Session
) -> None:
    """Inactive users cannot log in."""
    user = users[UserRole.STUDENT]
    user.is_active = False
    db.commit()
    response = client.post(f"{API}/login", json={"email": user.email, "password": PASSWORD})
    assert response.status_code == 401


def test_refresh_rotation(
    client: TestClient, users: dict[UserRole, User], db: Session
) -> None:
    """Refresh issues a new pair and revokes the old token; reuse revokes the family."""
    tokens = _login(client, users[UserRole.STUDENT].email)
    first = client.post(f"{API}/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200
    new_tokens = first.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    assert client.get(
        f"{API}/me", headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
    ).status_code == 200

    reuse = client.post(f"{API}/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuse.status_code == 401
    # Theft detection: the newer token is now revoked too.
    again = client.post(f"{API}/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    assert again.status_code == 401


def test_refresh_invalid_and_expired(
    client: TestClient, users: dict[UserRole, User], db: Session
) -> None:
    """Garbage and expired refresh tokens are rejected."""
    assert client.post(f"{API}/refresh", json={"refresh_token": "garbage"}).status_code == 401
    tokens = _login(client, users[UserRole.STUDENT].email)
    row = db.execute(select(RefreshToken)).scalar_one()
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    response = client.post(f"{API}/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 401


def test_access_token_not_valid_for_refresh(
    client: TestClient, users: dict[UserRole, User]
) -> None:
    """An access token cannot be used to refresh."""
    tokens = _login(client, users[UserRole.STUDENT].email)
    response = client.post(f"{API}/refresh", json={"refresh_token": tokens["access_token"]})
    assert response.status_code == 401


def test_logout_revokes(
    client: TestClient, users: dict[UserRole, User], db: Session
) -> None:
    """Logout returns 204 and the refresh token can no longer be used."""
    tokens = _login(client, users[UserRole.STUDENT].email)
    response = client.post(f"{API}/logout", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 204
    assert client.post(
        f"{API}/refresh", json={"refresh_token": tokens["refresh_token"]}
    ).status_code == 401
    assert "LOGOUT" in _actions(db)
    # idempotent for unknown tokens
    assert client.post(f"{API}/logout", json={"refresh_token": "unknown"}).status_code == 204


def test_me_get_and_update(
    client: TestClient,
    users: dict[UserRole, User],
    auth_headers: Callable[[User], dict[str, str]],
) -> None:
    """GET /me returns the profile; PUT /me updates the name only."""
    user = users[UserRole.STUDENT]
    headers = auth_headers(user)
    got = client.get(f"{API}/me", headers=headers)
    assert got.status_code == 200
    assert got.json()["email"] == user.email
    assert "password" not in got.text

    updated = client.put(f"{API}/me", headers=headers, json={"full_name": "Renamed"})
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Renamed"
    assert updated.json()["role"] == "STUDENT"


def test_me_requires_auth(client: TestClient) -> None:
    """Unauthenticated /me gives 401."""
    assert client.get(f"{API}/me").status_code == 401
    assert client.put(f"{API}/me", json={"full_name": "x"}).status_code == 401


def test_forgot_password_no_enumeration(
    client: TestClient, users: dict[UserRole, User], db: Session
) -> None:
    """Known and unknown emails both return 202."""
    known = client.post(f"{API}/forgot-password", json={"email": users[UserRole.STUDENT].email})
    unknown = client.post(f"{API}/forgot-password", json={"email": "ghost@example.com"})
    assert known.status_code == 202
    assert unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(db.execute(select(PasswordResetToken)).scalars().all()) == 1


def test_forgot_and_reset_password(
    client: TestClient,
    users: dict[UserRole, User],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Full reset flow: token works once, old sessions revoked, new password works."""
    user = users[UserRole.STUDENT]
    sent: dict[str, str] = {}
    monkeypatch.setattr(
        email_service,
        "send_password_reset_email",
        lambda to, token: sent.update(to=to, token=token) or True,
    )
    tokens = _login(client, user.email)
    assert client.post(f"{API}/forgot-password", json={"email": user.email}).status_code == 202
    assert sent["to"] == user.email

    stored = db.execute(select(PasswordResetToken)).scalar_one()
    assert stored.token_hash != sent["token"]

    new_password = "BrandNewPass456"
    response = client.post(
        f"{API}/reset-password", json={"token": sent["token"], "new_password": new_password}
    )
    assert response.status_code == 204
    # token single use
    assert client.post(
        f"{API}/reset-password", json={"token": sent["token"], "new_password": new_password}
    ).status_code == 400
    # old refresh revoked, old password rejected, new accepted
    assert client.post(
        f"{API}/refresh", json={"refresh_token": tokens["refresh_token"]}
    ).status_code == 401
    assert client.post(
        f"{API}/login", json={"email": user.email, "password": PASSWORD}
    ).status_code == 401
    _login(client, user.email, new_password)
    actions = _actions(db)
    assert "PASSWORD_RESET_REQUESTED" in actions
    assert "PASSWORD_RESET" in actions


def test_reset_password_invalid_and_expired(
    client: TestClient,
    users: dict[UserRole, User],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bad or expired tokens give 400."""
    bad = client.post(
        f"{API}/reset-password", json={"token": "bad", "new_password": "NewPassword1"}
    )
    assert bad.status_code == 400
    sent: dict[str, str] = {}
    monkeypatch.setattr(
        email_service,
        "send_password_reset_email",
        lambda to, token: sent.update(token=token) or True,
    )
    client.post(f"{API}/forgot-password", json={"email": users[UserRole.STUDENT].email})
    row = db.execute(select(PasswordResetToken)).scalar_one()
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    expired = client.post(
        f"{API}/reset-password", json={"token": sent["token"], "new_password": "NewPassword1"}
    )
    assert expired.status_code == 400


def test_email_skipped_without_smtp_and_never_logs_token(
    client: TestClient,
    users: dict[UserRole, User],
    db: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With no SMTP_HOST the email is skipped and no secret appears in logs."""
    assert settings.SMTP_HOST == ""
    with caplog.at_level(logging.DEBUG):
        client.post(f"{API}/forgot-password", json={"email": users[UserRole.STUDENT].email})
    assert any("email skipped" in r.getMessage() for r in caplog.records)
    token_hash = db.execute(select(PasswordResetToken.token_hash)).scalar_one()
    assert token_hash not in caplog.text
    assert "reset-password?token" not in caplog.text


def test_send_email_smtp_failure_is_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    """SMTP errors are logged without raising."""
    import smtplib

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.invalid")

    def boom(*args: object, **kwargs: object) -> None:
        raise smtplib.SMTPException("fail")

    monkeypatch.setattr(smtplib, "SMTP", boom)
    assert email_service.send_email("a@example.com", "s", "b") is False


def test_send_email_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """SMTP happy path sends once."""
    import smtplib

    calls: list[str] = []

    class FakeSMTP:
        def __init__(self, *args: object, **kwargs: object) -> None:
            calls.append("init")

        def __enter__(self) -> "FakeSMTP":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def starttls(self) -> None:
            calls.append("tls")

        def login(self, user: str, password: str) -> None:
            calls.append("login")

        def send_message(self, message: object) -> None:
            calls.append("send")

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_USER", "u")
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    assert email_service.send_email("a@example.com", "s", "b") is True
    assert calls == ["init", "tls", "login", "send"]


def test_rate_limit_login(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Login is rate limited with 429 and the standard error body."""
    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT", "2/minute")
    limiter.enabled = True
    limiter.reset()
    try:
        codes = [
            client.post(
                f"{API}/login", json={"email": "x@example.com", "password": "pw"}
            ).status_code
            for _ in range(3)
        ]
    finally:
        limiter.enabled = False
        limiter.reset()
    assert codes == [401, 401, 429]
