"""phase 1: departments, students, academic records, projects, certifications,
faculty assignments

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ts() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def _college_fk() -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(["college_id"], ["colleges.id"], ondelete="RESTRICT")


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_ts(),
        _college_fk(),
        sa.UniqueConstraint("college_id", "code", name="uq_departments_college_code"),
    )
    op.create_index("ix_departments_college_id", "departments", ["college_id"])

    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("roll_number", sa.String(50), nullable=True),
        sa.Column("graduation_year", sa.Integer(), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("college_id", "roll_number", name="uq_students_college_roll"),
    )
    op.create_index("ix_students_college_id", "students", ["college_id"])
    op.create_index("ix_students_department_id", "students", ["department_id"])

    op.create_table(
        "academic_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        sa.Column("cgpa", sa.Numeric(4, 2), nullable=False),
        sa.Column("active_arrears", sa.Integer(), server_default="0", nullable=False),
        sa.Column("attendance_pct", sa.Numeric(5, 2), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.UniqueConstraint("student_id", "semester", name="uq_academic_records_student_sem"),
    )
    op.create_index("ix_academic_records_student_id", "academic_records", ["student_id"])
    op.create_index("ix_academic_records_college_id", "academic_records", ["college_id"])

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("url", sa.String(500), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        _college_fk(),
    )
    op.create_index("ix_projects_student_id", "projects", ["student_id"])
    op.create_index("ix_projects_college_id", "projects", ["college_id"])

    op.create_table(
        "certifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("issuer", sa.String(255), nullable=True),
        sa.Column("issued_on", sa.Date(), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        _college_fk(),
    )
    op.create_index("ix_certifications_student_id", "certifications", ["student_id"])
    op.create_index("ix_certifications_college_id", "certifications", ["college_id"])

    op.create_table(
        "faculty_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("faculty_user_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        *_ts(),
        _college_fk(),
        sa.ForeignKeyConstraint(["faculty_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("faculty_user_id", "student_id", name="uq_faculty_assignments_pair"),
    )
    op.create_index("ix_faculty_assignments_college_id", "faculty_assignments", ["college_id"])
    op.create_index(
        "ix_faculty_assignments_faculty_user_id", "faculty_assignments", ["faculty_user_id"]
    )
    op.create_index("ix_faculty_assignments_student_id", "faculty_assignments", ["student_id"])


def downgrade() -> None:
    op.drop_table("faculty_assignments")
    op.drop_table("certifications")
    op.drop_table("projects")
    op.drop_table("academic_records")
    op.drop_table("students")
    op.drop_table("departments")
