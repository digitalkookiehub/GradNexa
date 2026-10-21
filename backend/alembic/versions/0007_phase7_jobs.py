"""phase 7: companies, job descriptions, job skills, eligibility rules

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
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
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("website", sa.String(2048), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_ts(),
        _college_fk(),
        sa.UniqueConstraint("college_id", "name", name="uq_companies_college_name"),
    )
    op.create_index("ix_companies_college_id", "companies", ["college_id"])

    op.create_table(
        "job_descriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "OPEN", "CLOSED", name="jobstatus"),
            server_default="DRAFT",
            nullable=False,
        ),
        sa.Column("application_deadline", sa.Date(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        *_ts(),
        _college_fk(),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["career_roles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_job_descriptions_college_id", "job_descriptions", ["college_id"])
    op.create_index("ix_job_descriptions_company_id", "job_descriptions", ["company_id"])
    op.create_index("ix_job_descriptions_role_id", "job_descriptions", ["role_id"])
    op.create_index("ix_job_descriptions_status", "job_descriptions", ["status"])
    op.create_index("ix_job_descriptions_created_by", "job_descriptions", ["created_by"])

    op.create_table(
        "job_skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("required_level", sa.Numeric(5, 2), nullable=False),
        sa.Column("weight", sa.Numeric(5, 2), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["job_id"], ["job_descriptions.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("job_id", "skill_id", name="uq_job_skills_job_skill"),
        sa.CheckConstraint(
            "required_level >= 0 AND required_level <= 100", name="ck_job_skills_required_level"
        ),
        sa.CheckConstraint("weight > 0", name="ck_job_skills_weight"),
    )
    op.create_index("ix_job_skills_job_id", "job_skills", ["job_id"])
    op.create_index("ix_job_skills_college_id", "job_skills", ["college_id"])
    op.create_index("ix_job_skills_skill_id", "job_skills", ["skill_id"])

    op.create_table(
        "eligibility_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("cgpa_min", sa.Numeric(4, 2), nullable=True),
        sa.Column(
            "cgpa_basis",
            sa.Enum("LATEST_SEMESTER", "AVERAGE_ALL_SEMESTERS", name="cgpabasis"),
            nullable=True,
        ),
        sa.Column("max_arrears", sa.Integer(), nullable=True),
        sa.Column("attendance_min", sa.Numeric(5, 2), nullable=True),
        sa.Column("department_ids", sa.JSON(), nullable=True),
        sa.Column("graduation_years", sa.JSON(), nullable=True),
        sa.Column("custom_notes", sa.JSON(), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["job_id"], ["job_descriptions.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.UniqueConstraint("job_id", name="uq_eligibility_rules_job_id"),
        sa.CheckConstraint(
            "cgpa_min IS NULL OR (cgpa_min >= 0 AND cgpa_min <= 10)",
            name="ck_eligibility_rules_cgpa_min",
        ),
        sa.CheckConstraint(
            "max_arrears IS NULL OR max_arrears >= 0", name="ck_eligibility_rules_max_arrears"
        ),
        sa.CheckConstraint(
            "attendance_min IS NULL OR (attendance_min >= 0 AND attendance_min <= 100)",
            name="ck_eligibility_rules_attendance_min",
        ),
    )
    op.create_index("ix_eligibility_rules_college_id", "eligibility_rules", ["college_id"])


def downgrade() -> None:
    op.drop_table("eligibility_rules")
    op.drop_table("job_skills")
    op.drop_table("job_descriptions")
    op.drop_table("companies")
    bind = op.get_bind()
    sa.Enum(name="cgpabasis").drop(bind, checkfirst=True)
    sa.Enum(name="jobstatus").drop(bind, checkfirst=True)
