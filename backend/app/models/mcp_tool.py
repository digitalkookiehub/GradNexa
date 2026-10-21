from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MCPTool(Base, TimestampMixin):
    """Per-college enable/disable override for an MCP tool.

    Tool definitions live in code; this table only stores overrides.
    """

    __tablename__ = "mcp_tools"
    __table_args__ = (UniqueConstraint("college_id", "name", name="uq_mcp_tools_college_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
