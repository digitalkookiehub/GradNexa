"""ADMIN: per-college enable/disable overrides for MCP tools."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.mcp import registry
from app.models import MCPTool, User, UserRole
from app.schemas.mcp import AdminToolItem, AdminToolUpdate
from app.services import audit_service

router = APIRouter(prefix="/admin/mcp-tools", tags=["admin-mcp"])
AdminUser = Depends(require_role(UserRole.ADMIN))


def _item(d: registry.ToolDef, enabled: bool) -> AdminToolItem:
    return AdminToolItem(
        name=d.name,
        description=d.description,
        allowed_roles=sorted(r.value for r in d.allowed_roles),
        enabled=enabled,
    )


@router.get("", response_model=list[AdminToolItem])
async def list_tools(
    admin: User = AdminUser, db: Session = Depends(get_db)
) -> list[AdminToolItem]:
    """All tools with the college enable flag."""
    over = registry.overrides(db, admin.college_id)
    return [_item(d, over.get(d.name, True)) for d in registry.REGISTRY.values()]


@router.put("/{name}", response_model=AdminToolItem)
async def set_tool(
    name: str,
    payload: AdminToolUpdate,
    admin: User = AdminUser,
    db: Session = Depends(get_db),
) -> AdminToolItem:
    """Upsert the college override for a tool."""
    tool = registry.get_tool(name)
    row = db.execute(
        select(MCPTool).where(MCPTool.college_id == admin.college_id, MCPTool.name == name)
    ).scalar_one_or_none()
    if row is None:
        db.add(MCPTool(college_id=admin.college_id, name=name, is_enabled=payload.enabled))
    else:
        row.is_enabled = payload.enabled
    audit_service.record(
        db, registry.MCP_TOOL_TOGGLE, "mcp_tool", user_id=admin.id,
        college_id=admin.college_id, resource_id=name, metadata={"enabled": payload.enabled},
    )
    db.commit()
    return _item(tool, payload.enabled)
