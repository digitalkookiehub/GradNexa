"""Pydantic schemas for departments."""
from pydantic import BaseModel, ConfigDict, Field


class DepartmentCreate(BaseModel):
    """Payload to create a department."""

    name: str = Field(min_length=1, max_length=150)
    code: str = Field(min_length=1, max_length=20)


class DepartmentUpdate(BaseModel):
    """Payload to update a department."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    code: str | None = Field(default=None, min_length=1, max_length=20)
    is_active: bool | None = None


class DepartmentResponse(BaseModel):
    """Department representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    college_id: int
    name: str
    code: str
    is_active: bool
