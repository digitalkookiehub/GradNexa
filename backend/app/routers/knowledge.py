"""Knowledge search for any authenticated user (lexical retrieval with citations)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.knowledge import SearchRequest, SearchResponse
from app.services import knowledge_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    payload: SearchRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> SearchResponse:
    """Search approved documents; returns citable passages or insufficient_evidence."""
    return knowledge_service.search_for_user(db, user, payload.query, payload.top_k)
