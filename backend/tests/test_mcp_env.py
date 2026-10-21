"""Shared scenario environment for the MCP and assistant tests (no tests of its own)."""
import hashlib
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    AcademicRecord,
    CareerRole,
    College,
    Department,
    FacultyAssignment,
    RAGChunk,
    RAGDocument,
    RagDocumentStatus,
    RagSourceType,
    Student,
    StudentCareerGoal,
    User,
    UserRole,
)
from app.models.company import Company
from app.models.eligibility_rule import CgpaBasis, EligibilityRule
from app.models.job_description import JobDescription, JobStatus
from app.models.job_skill import JobSkill
from tests.test_readiness_api import Env as BaseEnv

Headers = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


class McpEnv(BaseEnv):
    """Readiness Env plus student rows, jobs, companies, assignments and knowledge."""

    def setup_students(self) -> None:
        self.dept_a = self.dept(self.a, "CS")
        self.s1 = self.student_row(self.student, self.dept_a)
        self.s2 = self.student_row(self.student2, self.dept_a)
        self.sb = self.student_row(self.student_b, self.dept(self.b, "CS"))
        self.s1.roll_number = "R-ONE"
        self.s1.graduation_year = 2027
        self.db.add(
            AcademicRecord(
                student_id=self.s1.id, college_id=self.a.id, semester=3,
                cgpa=Decimal("8.10"), active_arrears=0, attendance_pct=Decimal("88"),
            )
        )
        self.db.commit()
        self.student2.full_name = "Secret Other Person"
        self.student2.email = "secret.other@a.example.com"
        self.db.commit()

    def assign(self, faculty: User, student: Student) -> None:
        self.db.add(
            FacultyAssignment(
                college_id=self.a.id, faculty_user_id=faculty.id, student_id=student.id
            )
        )
        self.db.commit()

    def company_job(
        self, college: College, status: JobStatus = JobStatus.OPEN, name: str = "Acme",
        role_id: int | None = None, with_rule: bool = True,
    ) -> JobDescription:
        creator = self.admin if college.id == self.a.id else self.admin_b
        company = Company(college_id=college.id, name=name)
        self.db.add(company)
        self.db.commit()
        job = JobDescription(
            college_id=college.id, company_id=company.id, role_id=role_id, title=f"{name} Job",
            body="Build things", status=status, application_deadline=date(2099, 1, 1),
            created_by=creator.id,
        )
        self.db.add(job)
        self.db.commit()
        skill = self.py if college.id == self.a.id else None
        if skill is not None:
            self.db.add(
                JobSkill(
                    job_id=job.id, college_id=college.id, skill_id=skill.id,
                    required_level=Decimal("60"), weight=Decimal("1"),
                )
            )
        if with_rule:
            self.db.add(
                EligibilityRule(
                    job_id=job.id, college_id=college.id, cgpa_min=Decimal("7.5"),
                    cgpa_basis=CgpaBasis.LATEST_SEMESTER, max_arrears=0,
                )
            )
        self.db.commit()
        return job

    def goal(self, student: Student, role_id: int) -> None:
        self.db.add(
            StudentCareerGoal(
                student_id=student.id, college_id=student.college_id,
                career_role_id=role_id, priority=1,
            )
        )
        self.db.commit()

    def doc(
        self, college: College, title: str, text: str,
        status: RagDocumentStatus = RagDocumentStatus.APPROVED,
        department_id: int | None = None,
    ) -> RAGDocument:
        key = hashlib.sha256((title + str(college.id) + text).encode()).hexdigest()
        doc = RAGDocument(
            college_id=college.id, title=title, source_type=RagSourceType.PLACEMENT_GUIDE,
            department_id=department_id, original_filename="f.txt", content_type="text/plain",
            size_bytes=len(text), sha256=key, storage_key=key, status=status,
            uploaded_by=self.admin.id, chunk_count=1,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.add(
            RAGChunk(
                document_id=doc.id, college_id=college.id, chunk_index=0, content=text,
                token_count=len(text.split()), char_start=0, char_end=len(text),
            )
        )
        self.db.commit()
        return doc

    def call(self, name: str, user: User, args: dict[str, Any] | None = None) -> Any:
        return self.req("POST", f"/mcp/tools/{name}/call", user, json={"arguments": args or {}})

    def ask(self, user: User, question: str, **kw: Any) -> Any:
        return self.req("POST", "/assistant/query", user, json={"question": question, **kw})

    def role_named(self, name: str = "Data Analyst") -> int:
        role = self.role(name)
        self.role_skills(role)
        return role

    def other_role(self) -> CareerRole:
        obj = CareerRole(college_id=self.b.id, name="B Role")
        self.db.add(obj)
        self.db.commit()
        return obj


@pytest.fixture
def menv(
    client: TestClient, db: Session, auth_headers: Headers, make_user: MakeUser,
    college: College, other_college: College,
) -> McpEnv:
    """Scenario with students, departments and one academic record."""
    e = McpEnv(client, db, auth_headers, make_user, college, other_college)
    e.setup_students()
    return e


__all__ = ["McpEnv", "Department", "UserRole", "menv"]
