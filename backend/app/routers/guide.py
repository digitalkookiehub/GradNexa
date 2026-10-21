"""In-app user guide (access limited to GUIDE_ROLES)."""
from fastapi import APIRouter, Depends

from app.dependencies import require_role
from app.models import User
from app.schemas.guide import GuideResponse
from app.services import guide_service

router = APIRouter(prefix="/guide", tags=["guide"])


@router.get("", response_model=GuideResponse)
async def get_guide(_: User = Depends(require_role(*guide_service.GUIDE_ROLES))) -> GuideResponse:
    """Return the user guide for roles allowed to read it."""
    return guide_service.read_guide()
