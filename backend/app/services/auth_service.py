"""Authentication business logic."""
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.config import settings
from app.exceptions import AppError, ConflictError, NotFoundError, UnauthorizedError
from app.models import College, PasswordResetToken, RefreshToken, User, UserRole
from app.schemas.auth import TokenResponse
from app.services import audit_service, email_service

logger = logging.getLogger(__name__)

# Used to equalise timing when the account does not exist.
_DUMMY_HASH = hash_password("not-a-real-password")


def _aware(value: datetime) -> datetime:
    """Defensive: treat a naive datetime as UTC (columns are timezone-aware in PostgreSQL)."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()


def register_user(
    db: Session, email: str, password: str, full_name: str, college_code: str
) -> User:
    """Create a STUDENT user in the college identified by college_code."""
    college = db.execute(
        select(College).where(College.code == college_code, College.is_active.is_(True))
    ).scalar_one_or_none()
    if college is None:
        raise NotFoundError("College not found")
    if _get_user_by_email(db, email) is not None:
        raise ConflictError("Email already registered")
    user = User(
        college_id=college.id,
        email=email.lower(),
        hashed_password=hash_password(password),
        full_name=full_name.strip(),
        role=UserRole.STUDENT,
    )
    db.add(user)
    db.flush()
    audit_service.record(
        db,
        audit_service.REGISTER,
        "user",
        user_id=user.id,
        college_id=college.id,
        resource_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user


def _issue_tokens(db: Session, user: User) -> TokenResponse:
    refresh = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh),
            expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    access = create_access_token(user.id, user.role.value, user.college_id)
    return TokenResponse(access_token=access, refresh_token=refresh)


def login(db: Session, email: str, password: str) -> TokenResponse:
    """Authenticate by email/password and issue a token pair."""
    user = _get_user_by_email(db, email)
    stored = user.hashed_password if user and user.hashed_password else _DUMMY_HASH
    valid = verify_password(password, stored)
    if user is None or not valid or not user.is_active:
        audit_service.record(
            db,
            audit_service.LOGIN_FAILED,
            "user",
            user_id=user.id if user else None,
            college_id=user.college_id if user else None,
            resource_id=user.id if user else None,
        )
        db.commit()
        raise UnauthorizedError("Invalid email or password")
    tokens = _issue_tokens(db, user)
    audit_service.record(
        db,
        audit_service.LOGIN,
        "user",
        user_id=user.id,
        college_id=user.college_id,
        resource_id=user.id,
    )
    db.commit()
    return tokens


def _revoke_all(db: Session, user_id: int) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )


def refresh_tokens(db: Session, refresh_token: str) -> TokenResponse:
    """Rotate a refresh token: revoke the old one and issue a new pair."""
    invalid = UnauthorizedError("Invalid refresh token")
    if decode_token(refresh_token, "refresh") is None:
        raise invalid
    row = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    ).scalar_one_or_none()
    if row is None:
        raise invalid
    if row.revoked:
        # Reuse of a revoked token suggests theft: revoke the whole family.
        _revoke_all(db, row.user_id)
        db.commit()
        raise invalid
    user = db.get(User, row.user_id)
    if _aware(row.expires_at) < datetime.now(UTC) or user is None or not user.is_active:
        raise invalid
    row.revoked = True
    tokens = _issue_tokens(db, user)
    audit_service.record(
        db,
        audit_service.TOKEN_REFRESH,
        "user",
        user_id=user.id,
        college_id=user.college_id,
        resource_id=user.id,
    )
    db.commit()
    return tokens


def logout(db: Session, refresh_token: str) -> None:
    """Revoke a refresh token. Idempotent; unknown tokens are ignored."""
    row = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    ).scalar_one_or_none()
    if row is None:
        return
    row.revoked = True
    user = db.get(User, row.user_id)
    audit_service.record(
        db,
        audit_service.LOGOUT,
        "user",
        user_id=row.user_id,
        college_id=user.college_id if user else None,
        resource_id=row.user_id,
    )
    db.commit()


def request_password_reset(db: Session, email: str) -> None:
    """Create a reset token and email it. Silent if the account does not exist."""
    user = _get_user_by_email(db, email)
    if user is None or not user.is_active:
        return
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used.is_(False))
        .values(used=True)
    )
    token = generate_opaque_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC)
            + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
        )
    )
    audit_service.record(
        db,
        audit_service.PASSWORD_RESET_REQUESTED,
        "user",
        user_id=user.id,
        college_id=user.college_id,
        resource_id=user.id,
    )
    db.commit()
    email_service.send_password_reset_email(user.email, token)


def reset_password(db: Session, token: str, new_password: str) -> None:
    """Set a new password using a valid reset token; revokes all sessions."""
    row = db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(token))
    ).scalar_one_or_none()
    if row is None or row.used or _aware(row.expires_at) < datetime.now(UTC):
        raise AppError("Invalid or expired reset token")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise AppError("Invalid or expired reset token")
    user.hashed_password = hash_password(new_password)
    row.used = True
    _revoke_all(db, user.id)
    audit_service.record(
        db,
        audit_service.PASSWORD_RESET,
        "user",
        user_id=user.id,
        college_id=user.college_id,
        resource_id=user.id,
    )
    db.commit()


def update_profile(db: Session, user: User, full_name: str) -> User:
    """Update the caller profile."""
    user.full_name = full_name.strip()
    audit_service.record(
        db,
        audit_service.PROFILE_UPDATE,
        "user",
        user_id=user.id,
        college_id=user.college_id,
        resource_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user
