"""Shared dependencies and rate limiter."""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth.dependencies import (
    TenantContext,
    get_college_id,
    get_current_user,
    get_tenant,
    require_role,
    scope_to_college,
)
from app.config import settings
from app.database import get_db

limiter = Limiter(key_func=get_remote_address, enabled=settings.RATE_LIMIT_ENABLED)

__all__ = [
    "TenantContext",
    "get_college_id",
    "get_current_user",
    "get_db",
    "get_tenant",
    "limiter",
    "require_role",
    "scope_to_college",
]
