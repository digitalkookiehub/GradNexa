"""Auth dependencies: current user, RBAC and tenant scoping."""
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Select
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.database import get_db
from app.exceptions import ForbiddenError, UnauthorizedError
from app.models import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated, active user from the Bearer access token."""
    if credentials is None:
        raise UnauthorizedError("Not authenticated")
    payload = decode_token(credentials.credentials, "access")
    if payload is None:
        raise UnauthorizedError("Invalid or expired token")
    try:
        user_id = int(str(payload.get("sub")))
    except ValueError as exc:
        raise UnauthorizedError("Invalid token") from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return user


def require_role(*roles: UserRole) -> Callable[..., Any]:
    """Build a dependency that allows only the given roles (SUPER_ADMIN is not implicit)."""
    allowed = set(roles)

    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise ForbiddenError("Insufficient permissions")
        return user

    return checker


@dataclass(frozen=True)
class TenantContext:
    """The caller and the college every query must be scoped to."""

    user: User
    college_id: int


async def get_tenant(user: User = Depends(get_current_user)) -> TenantContext:
    """Expose the caller college_id for tenant-scoped queries."""
    return TenantContext(user=user, college_id=user.college_id)


async def get_college_id(tenant: TenantContext = Depends(get_tenant)) -> int:
    """Dependency returning just the caller college_id."""
    return tenant.college_id


def scope_to_college(stmt: Select[Any], model: Any, college_id: int) -> Select[Any]:
    """Add a college_id filter to a select statement on a tenant-owned model."""
    return stmt.where(model.college_id == college_id)
