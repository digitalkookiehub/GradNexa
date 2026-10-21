"""Health endpoints."""
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(db: Session = Depends(get_db)) -> JSONResponse:
    """Readiness probe: verifies database connectivity (503 if down)."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Readiness check failed")
        return JSONResponse({"detail": "Database unavailable"}, status_code=503)
    return JSONResponse({"status": "ready"})
