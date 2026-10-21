"""phase 6: resumes, resume analyses, interview questions, mock interviews, answers, results

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
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
        "resumes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("extracted_text", sa.Text(), server_default="", nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column(
            "uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_resumes_student_id", "resumes", ["student_id"])
    op.create_index("ix_resumes_college_id", "resumes", ["college_id"])

    op.create_table(
        "resume_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=True),
        sa.Column("extractor_version", sa.String(50), nullable=False),
        sa.Column("extracted", sa.JSON(), nullable=False),
        sa.Column("role_match", sa.JSON(), nullable=True),
        sa.Column("jd_match", sa.JSON(), nullable=True),
        sa.Column("notes", sa.JSON(), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.ForeignKeyConstraint(["role_id"], ["career_roles.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_resume_analyses_resume_id", "resume_analyses", ["resume_id"])
    op.create_index("ix_resume_analyses_student_id", "resume_analyses", ["student_id"])
    op.create_index("ix_resume_analyses_college_id", "resume_analyses", ["college_id"])
    op.create_index("ix_resume_analyses_role_id", "resume_analyses", ["role_id"])

    op.create_table(
        "interview_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=True),
        sa.Column("skill_id", sa.Integer(), nullable=True),
        sa.Column("competency", sa.String(100), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("rubric", sa.JSON(), nullable=False),
        sa.Column("min_words", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        *_ts(),
        _college_fk(),
        sa.ForeignKeyConstraint(["role_id"], ["career_roles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("min_words >= 0", name="ck_interview_questions_min_words"),
    )
    op.create_index("ix_interview_questions_college_id", "interview_questions", ["college_id"])
    op.create_index("ix_interview_questions_role_id", "interview_questions", ["role_id"])
    op.create_index("ix_interview_questions_skill_id", "interview_questions", ["skill_id"])
    op.create_index("ix_interview_questions_created_by", "interview_questions", ["created_by"])

    op.create_table(
        "mock_interviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("IN_PROGRESS", "COMPLETED", name="interviewstatus"),
            server_default="IN_PROGRESS",
            nullable=False,
        ),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.ForeignKeyConstraint(["role_id"], ["career_roles.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_mock_interviews_student_id", "mock_interviews", ["student_id"])
    op.create_index("ix_mock_interviews_college_id", "mock_interviews", ["college_id"])
    op.create_index("ix_mock_interviews_role_id", "mock_interviews", ["role_id"])

    op.create_table(
        "interview_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("interview_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["interview_id"], ["mock_interviews.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.ForeignKeyConstraint(["question_id"], ["interview_questions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "interview_id", "question_id", name="uq_interview_answers_interview_question"
        ),
        sa.CheckConstraint("position >= 1", name="ck_interview_answers_position"),
    )
    op.create_index("ix_interview_answers_interview_id", "interview_answers", ["interview_id"])
    op.create_index("ix_interview_answers_college_id", "interview_answers", ["college_id"])
    op.create_index("ix_interview_answers_question_id", "interview_answers", ["question_id"])

    op.create_table(
        "interview_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("interview_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("overall", sa.Numeric(5, 2), nullable=True),
        sa.Column("competency_scores", sa.JSON(), nullable=False),
        sa.Column("per_question", sa.JSON(), nullable=False),
        sa.Column("scoring_version", sa.String(50), nullable=False),
        sa.Column(
            "computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        *_ts(),
        sa.ForeignKeyConstraint(["interview_id"], ["mock_interviews.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["career_roles.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("interview_id"),
    )
    op.create_index("ix_interview_results_college_id", "interview_results", ["college_id"])
    op.create_index("ix_interview_results_student_id", "interview_results", ["student_id"])
    op.create_index("ix_interview_results_role_id", "interview_results", ["role_id"])


def downgrade() -> None:
    op.drop_table("interview_results")
    op.drop_table("interview_answers")
    op.drop_table("mock_interviews")
    op.drop_table("interview_questions")
    op.drop_table("resume_analyses")
    op.drop_table("resumes")
    bind = op.get_bind()
    sa.Enum(name="interviewstatus").drop(bind, checkfirst=True)
