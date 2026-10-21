"""In-app user guide: content and who may read it."""
import json
from pathlib import Path

from pydantic import ValidationError

from app.exceptions import NotFoundError
from app.models import UserRole
from app.schemas.guide import GuideDocument, GuideResponse

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
FLOW_PATH = CONTENT_DIR / "guide.json"
GUIDE_PATH = CONTENT_DIR / "user_guide.md"

# Single place that decides who can read the guide. Today: ADMIN only. To let an admin grant
# access to other users later, replace this static set with a per-college setting.
GUIDE_ROLES: tuple[UserRole, ...] = (UserRole.ADMIN,)


def load_document() -> GuideDocument:
    """Load and validate the structured flow content."""
    try:
        return GuideDocument.model_validate(json.loads(FLOW_PATH.read_text(encoding="utf-8")))
    except (OSError, ValueError, ValidationError) as exc:
        raise NotFoundError("User guide is not available") from exc


def read_guide() -> GuideResponse:
    """Return the structured flows plus the written (Markdown) guide."""
    doc = load_document()
    try:
        markdown = GUIDE_PATH.read_text(encoding="utf-8")
    except OSError:
        markdown = ""
    return GuideResponse(**doc.model_dump(), markdown=markdown)
