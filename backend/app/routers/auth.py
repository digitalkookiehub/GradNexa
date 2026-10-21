"""Authentication endpoints."""
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_current_user, get_db, limiter
from app.models import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit(lambda: settings.REGISTER_RATE_LIMIT)
async def register(
    request: Request, payload: RegisterRequest, db: Session = Depends(get_db)
) -> User:
    """Self-register a STUDENT in the college identified by college_code."""
    return auth_service.register_user(
        db, payload.email, payload.password, payload.full_name, payload.college_code
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(lambda: settings.LOGIN_RATE_LIMIT)
async def login(
    request: Request, payload: LoginRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    """Authenticate and return a token pair."""
    return auth_service.login(db, payload.email, payload.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Rotate the refresh token and return a new pair."""
    return auth_service.refresh_tokens(db, payload.refresh_token)


@router.post("/logout", status_code=204)
async def logout(payload: RefreshRequest, db: Session = Depends(get_db)) -> Response:
    """Revoke the given refresh token."""
    auth_service.logout(db, payload.refresh_token)
    return Response(status_code=204)


@router.post("/forgot-password", status_code=202)
@limiter.limit(lambda: settings.FORGOT_PASSWORD_RATE_LIMIT)
async def forgot_password(
    request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> dict[str, str]:
    """Request a password reset email. Always 202 to prevent account enumeration."""
    auth_service.request_password_reset(db, payload.email)
    return {"detail": "If the account exists, a reset email has been sent"}


@router.post("/reset-password", status_code=204)
async def reset_password(
    payload: ResetPasswordRequest, db: Session = Depends(get_db)
) -> Response:
    """Reset the password using a valid reset token."""
    auth_service.reset_password(db, payload.token, payload.new_password)
    return Response(status_code=204)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> User:
    """Return the current user."""
    return user


@router.put("/me", response_model=UserResponse)
async def update_me(
    payload: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Update the current user profile."""
    return auth_service.update_profile(db, user, payload.full_name)
