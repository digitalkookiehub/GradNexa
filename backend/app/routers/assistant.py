"""Deterministic AI assistant endpoint (STUDENT only)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.assistant import AssistantQuery, AssistantResponse
from app.services import assistant_service

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/query", response_model=AssistantResponse)
async def query(
    payload: AssistantQuery,
    user: User = Depends(require_role(UserRole.STUDENT)),
    db: Session = Depends(get_db),
) -> AssistantResponse:
    """Answer from stored deterministic results and cited approved passages (no LLM)."""
    return assistant_service.answer(db, user, payload)
