"""phase 2: skills, assessments, questions, attempts, results, student skills

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
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
        "skill_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column(
            "scope",
            sa.Enum("COMMON", "DEPARTMENT", name="skillscope"),
            server_default="COMMON",
            nullable=False,
        ),
        sa.Column("department_id", sa.Integer(), nullable=True),
        *_ts(),
        _college_fk(),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("college_id", "name", name="uq_skill_categories_college_name"),
    )
    op.create_index("ix_skill_categories_college_id", "skill_categories", ["college_id"])
    op.create_index("ix_skill_categories_department_id", "skill_categories", ["department_id"])

    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        *_ts(),
        _college_fk(),
        sa.ForeignKeyConstraint(["category_id"], ["skill_categories.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("college_id", "name", name="uq_skills_college_name"),
    )
    op.create_index("ix_skills_college_id", "skills", ["college_id"])
    op.create_index("ix_skills_category_id", "skills", ["category_id"])

    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("series_key", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "APTITUDE", "TECHNICAL", "COMMUNICATION", "ROLE_SPECIFIC",
                "DEPARTMENT_SPECIFIC", "CUSTOM",
                name="assessmenttype",
            ),
            nullable=False,
        ),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("time_limit_min", sa.Integer(), nullable=True),
        sa.Column("max_attempts", sa.Integer(), nullable=True),
        sa.Column("negative_marking", sa.Numeric(4, 2), server_default="0", nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "PUBLISHED", "ARCHIVED", name="assessmentstatus"),
            server_default="DRAFT",
            nullable=False,
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        *_ts(),
        _college_fk(),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("series_key", "version", name="uq_assessments_series_version"),
        sa.CheckConstraint("negative_marking >= 0", name="ck_assessments_negative_marking"),
    )
    op.create_index("ix_assessments_college_id", "assessments", ["college_id"])
    op.create_index("ix_assessments_series_key", "assessments", ["series_key"])
    op.create_index("ix_assessments_department_id", "assessments", ["department_id"])
    op.create_index("ix_assessments_created_by", "assessments", ["created_by"])

    op.create_table(
        "assessment_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column(
            "difficulty",
            sa.Enum("EASY", "MEDIUM", "HARD", name="questiondifficulty"),
            server_default="MEDIUM",
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("correct_option_ids", sa.JSON(), nullable=False),
        sa.Column("marks", sa.Numeric(5, 2), server_default="1", nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("marks >= 0", name="ck_assessment_questions_marks"),
    )
    op.create_index(
        "ix_assessment_questions_assessment_id", "assessment_questions", ["assessment_id"]
    )
    op.create_index("ix_assessment_questions_college_id", "assessment_questions", ["college_id"])
    op.create_index("ix_assessment_questions_skill_id", "assessment_questions", ["skill_id"])

    op.create_table(
        "assessment_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("IN_PROGRESS", "SUBMITTED", "EXPIRED", name="attemptstatus"),
            server_default="IN_PROGRESS",
            nullable=False,
        ),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("answers", sa.JSON(), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.UniqueConstraint(
            "assessment_id", "student_id", "attempt_no", name="uq_assessment_attempts_no"
        ),
    )
    op.create_index("ix_assessment_attempts_assessment_id", "assessment_attempts", ["assessment_id"])
    op.create_index("ix_assessment_attempts_student_id", "assessment_attempts", ["student_id"])
    op.create_index("ix_assessment_attempts_college_id", "assessment_attempts", ["college_id"])

    op.create_table(
        "assessment_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("assessment_version", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Numeric(7, 2), nullable=False),
        sa.Column("max_score", sa.Numeric(7, 2), nullable=False),
        sa.Column("percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("per_skill_scores", sa.JSON(), nullable=False),
        sa.Column(
            "computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        *_ts(),
        sa.ForeignKeyConstraint(["attempt_id"], ["assessment_attempts.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("attempt_id"),
    )
    op.create_index("ix_assessment_results_college_id", "assessment_results", ["college_id"])
    op.create_index("ix_assessment_results_student_id", "assessment_results", ["student_id"])
    op.create_index("ix_assessment_results_assessment_id", "assessment_results", ["assessment_id"])

    op.create_table(
        "student_skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("evidence_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_result_id", sa.Integer(), nullable=True),
        # Intentionally NULL until the Phase 3 readiness rules define confidence.
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_result_id"], ["assessment_results.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("student_id", "skill_id", name="uq_student_skills_student_skill"),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_student_skills_score"),
    )
    op.create_index("ix_student_skills_student_id", "student_skills", ["student_id"])
    op.create_index("ix_student_skills_college_id", "student_skills", ["college_id"])
    op.create_index("ix_student_skills_skill_id", "student_skills", ["skill_id"])
    op.create_index("ix_student_skills_last_result_id", "student_skills", ["last_result_id"])


def downgrade() -> None:
    op.drop_table("student_skills")
    op.drop_table("assessment_results")
    op.drop_table("assessment_attempts")
    op.drop_table("assessment_questions")
    op.drop_table("assessments")
    op.drop_table("skills")
    op.drop_table("skill_categories")
    bind = op.get_bind()
    for name in (
        "attemptstatus",
        "questiondifficulty",
        "assessmentstatus",
        "assessmenttype",
        "skillscope",
    ):
        sa.Enum(name=name).drop(bind, checkfirst=True)
