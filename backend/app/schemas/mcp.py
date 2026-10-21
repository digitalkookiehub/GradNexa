"""API schemas of the MCP endpoints."""
from typing import Any

from pydantic import BaseModel, Field


class ToolInfo(BaseModel):
    """A tool the caller may use."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    enabled: bool


class ToolCallRequest(BaseModel):
    """Tool call body."""

    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCallResponse(BaseModel):
    """Tool call result."""

    tool: str
    result: dict[str, Any]


class AdminToolItem(BaseModel):
    """Admin view of a tool."""

    name: str
    description: str
    allowed_roles: list[str]
    enabled: bool


class AdminToolUpdate(BaseModel):
    """Enable or disable a tool for the caller's college."""

    enabled: bool
