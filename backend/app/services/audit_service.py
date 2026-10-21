"""Audit logging service."""
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog

logger = logging.getLogger(__name__)

REGISTER = "REGISTER"
LOGIN = "LOGIN"
LOGIN_FAILED = "LOGIN_FAILED"
LOGOUT = "LOGOUT"
TOKEN_REFRESH = "TOKEN_REFRESH"
PASSWORD_RESET_REQUESTED = "PASSWORD_RESET_REQUESTED"
PASSWORD_RESET = "PASSWORD_RESET"
PROFILE_UPDATE = "PROFILE_UPDATE"


def record(
    db: Session,
    action: str,
    resource: str,
    *,
    user_id: int | None = None,
    college_id: int | None = None,
    resource_id: str | int | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Add an AuditLog row to the session (caller commits). Never pass secrets in metadata."""
    entry = AuditLog(
        college_id=college_id,
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=str(resource_id) if resource_id is not None else None,
        metadata_json=metadata,
    )
    db.add(entry)
    logger.info("audit action=%s resource=%s user_id=%s", action, resource, user_id)
    return entry
