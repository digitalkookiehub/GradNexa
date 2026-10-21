"""Pydantic schemas for authentication endpoints."""
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import UserRole


class RegisterRequest(BaseModel):
    """Self-registration payload (always creates a STUDENT)."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=150)
    college_code: str = Field(min_length=1, max_length=50)


class LoginRequest(BaseModel):
    """Login payload."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Access/refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Refresh/logout payload."""

    refresh_token: str = Field(min_length=1)


class ForgotPasswordRequest(BaseModel):
    """Forgot-password payload."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset-password payload."""

    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class UpdateProfileRequest(BaseModel):
    """Profile update payload."""

    full_name: str = Field(min_length=1, max_length=150)


class UserResponse(BaseModel):
    """Public user representation. Never contains password material."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    college_id: int
    is_active: bool
    is_verified: bool
