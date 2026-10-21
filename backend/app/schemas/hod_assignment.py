"""HOD-to-department assignment schemas."""
from pydantic import BaseModel


class HodAssignmentCreate(BaseModel):
    """Payload to assign a HOD user to a department."""

    hod_user_id: int
    department_id: int


class HodAssignmentOut(BaseModel):
    """One assignment with display names."""

    id: int
    hod_user_id: int
    hod_name: str
    hod_email: str
    department_id: int
    department_name: str
