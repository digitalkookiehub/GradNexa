"""Password hashing (bcrypt), JWT handling and opaque token hashing."""
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import settings


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode()[:72], salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode()[:72], hashed.encode())
    except ValueError:
        return False


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a token (only the hash is stored)."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_opaque_token() -> str:
    """Generate a random URL-safe token (used for password reset)."""
    return secrets.token_urlsafe(32)


def _encode(subject: str, token_type: str, expires: timedelta, extra: dict[str, object]) -> str:
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        **extra,
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: object, role: str, college_id: object) -> str:
    """Create a short-lived access JWT."""
    return _encode(
        str(user_id),
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        {"role": role, "college_id": str(college_id)},
    )


def create_refresh_token(user_id: object) -> str:
    """Create a long-lived refresh JWT (unique via jti)."""
    return _encode(str(user_id), "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), {})


def decode_token(token: str, expected_type: str) -> dict[str, object] | None:
    """Decode and validate a JWT; return None if invalid, expired or wrong type."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    return dict(payload)
