"""MCP tool endpoints: list tools for the caller's role and call them (read-only)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.mcp import registry
from app.models import User
from app.schemas.mcp import ToolCallRequest, ToolCallResponse, ToolInfo

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/tools", response_model=list[ToolInfo])
async def list_tools(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ToolInfo]:
    """Tools the caller's role may use, with schemas and the college enable flag."""
    over = registry.overrides(db, user.college_id)
    return [
        ToolInfo(
            name=d.name,
            description=d.description,
            input_schema=d.input_model.model_json_schema(),
            output_schema=d.output_model.model_json_schema(),
            enabled=over.get(d.name, True),
        )
        for d in registry.tools_for_role(user.role)
    ]


@router.post("/tools/{name}/call", response_model=ToolCallResponse)
async def call_tool(
    name: str,
    payload: ToolCallRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ToolCallResponse:
    """Call one tool as the authenticated user (authorised, validated and audited)."""
    out = registry.call_tool(db, user, name, payload.arguments)
    return ToolCallResponse(tool=name, result=out.model_dump(mode="json"))
