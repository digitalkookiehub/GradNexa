"""Pydantic schemas for the student and academic profile."""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class StudentUpdate(BaseModel):
    """Editable student profile fields."""

    department_id: int | None = None
    roll_number: str | None = Field(default=None, min_length=1, max_length=50)
    graduation_year: int | None = Field(default=None, ge=2000, le=2100)
    phone: str | None = Field(default=None, min_length=5, max_length=20)


class StudentResponse(BaseModel):
    """Student profile."""

    id: int
    user_id: int
    college_id: int
    department_id: int | None
    department_name: str | None
    roll_number: str | None
    graduation_year: int | None
    phone: str | None
    profile_complete: bool


class AcademicRecordCreate(BaseModel):
    """Create an academic record for a semester."""

    semester: int = Field(ge=1, le=12)
    cgpa: float = Field(ge=0, le=10)
    active_arrears: int = Field(default=0, ge=0)
    attendance_pct: float | None = Field(default=None, ge=0, le=100)


class AcademicRecordUpdate(BaseModel):
    """Update an academic record."""

    semester: int | None = Field(default=None, ge=1, le=12)
    cgpa: float | None = Field(default=None, ge=0, le=10)
    active_arrears: int | None = Field(default=None, ge=0)
    attendance_pct: float | None = Field(default=None, ge=0, le=100)


class AcademicRecordResponse(BaseModel):
    """Academic record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    semester: int
    cgpa: float
    active_arrears: int
    attendance_pct: float | None


class ProjectCreate(BaseModel):
    """Create a project."""

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    skills: list[str] = Field(default_factory=list, max_length=50)
    url: str | None = Field(default=None, max_length=500)


class ProjectResponse(BaseModel):
    """Project."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    title: str
    description: str | None
    skills: list[str]
    url: str | None


class CertificationCreate(BaseModel):
    """Create a certification."""

    name: str = Field(min_length=1, max_length=200)
    issuer: str | None = Field(default=None, max_length=200)
    issued_on: date | None = None


class CertificationResponse(BaseModel):
    """Certification."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    name: str
    issuer: str | None
    issued_on: date | None


class StudentDetailResponse(BaseModel):
    """Full student record for staff and the student themself."""

    profile: StudentResponse
    academic_records: list[AcademicRecordResponse]
    projects: list[ProjectResponse]
    certifications: list[CertificationResponse]


class FacultyAssignmentDetail(BaseModel):
    """Faculty assignment with the names needed to show it."""

    id: int
    faculty_user_id: int
    faculty_name: str
    faculty_email: str
    student_id: int
    student_name: str
    student_email: str


class FacultyAssignmentCreate(BaseModel):
    """Assign a student to a faculty member."""

    faculty_user_id: int
    student_id: int


class FacultyAssignmentResponse(BaseModel):
    """Faculty assignment."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    college_id: int
    faculty_user_id: int
    student_id: int
