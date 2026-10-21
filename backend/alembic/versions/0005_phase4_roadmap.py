"""phase 4: learning resources, career goals, learning plans and plan items

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
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
        "learning_resources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_approved", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        *_ts(),
        _college_fk(),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_learning_resources_college_id", "learning_resources", ["college_id"])
    op.create_index("ix_learning_resources_skill_id", "learning_resources", ["skill_id"])
    op.create_index("ix_learning_resources_approved_by", "learning_resources", ["approved_by"])
    op.create_index("ix_learning_resources_created_by", "learning_resources", ["created_by"])

    op.create_table(
        "student_career_goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("career_role_id", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.ForeignKeyConstraint(["career_role_id"], ["career_roles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "student_id", "career_role_id", name="uq_student_career_goals_student_role"
        ),
        sa.CheckConstraint("priority >= 1", name="ck_student_career_goals_priority"),
    )
    op.create_index("ix_student_career_goals_student_id", "student_career_goals", ["student_id"])
    op.create_index("ix_student_career_goals_college_id", "student_career_goals", ["college_id"])
    op.create_index(
        "ix_student_career_goals_career_role_id", "student_career_goals", ["career_role_id"]
    )

    op.create_table(
        "learning_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("baseline_readiness_score_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "COMPLETED", "ARCHIVED", name="planstatus"),
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("duration_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("skills_per_week", sa.Integer(), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.ForeignKeyConstraint(["role_id"], ["career_roles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["baseline_readiness_score_id"], ["readiness_scores.id"], ondelete="SET NULL"
        ),
        sa.CheckConstraint("skills_per_week >= 1", name="ck_learning_plans_skills_per_week"),
        sa.CheckConstraint("duration_days >= 1", name="ck_learning_plans_duration_days"),
    )
    op.create_index("ix_learning_plans_student_id", "learning_plans", ["student_id"])
    op.create_index("ix_learning_plans_college_id", "learning_plans", ["college_id"])
    op.create_index("ix_learning_plans_role_id", "learning_plans", ["role_id"])
    op.create_index(
        "ix_learning_plans_baseline_readiness_score_id",
        "learning_plans",
        ["baseline_readiness_score_id"],
    )
    op.create_index("ix_learning_plans_student_status", "learning_plans", ["student_id", "status"])

    op.create_table(
        "learning_plan_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("LEARN", "PRACTICE", "ASSESS", "REASSESS", name="planitemkind"),
            nullable=False,
        ),
        sa.Column("skill_id", sa.Integer(), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("TODO", "IN_PROGRESS", "DONE", name="planitemstatus"),
            server_default="TODO",
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.ForeignKeyConstraint(["plan_id"], ["learning_plans.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resource_id"], ["learning_resources.id"], ondelete="SET NULL"),
        sa.CheckConstraint("week >= 1 AND week <= 4", name="ck_learning_plan_items_week"),
    )
    op.create_index("ix_learning_plan_items_plan_id", "learning_plan_items", ["plan_id"])
    op.create_index("ix_learning_plan_items_college_id", "learning_plan_items", ["college_id"])
    op.create_index("ix_learning_plan_items_skill_id", "learning_plan_items", ["skill_id"])
    op.create_index("ix_learning_plan_items_resource_id", "learning_plan_items", ["resource_id"])


def downgrade() -> None:
    op.drop_table("learning_plan_items")
    op.drop_table("learning_plans")
    op.drop_table("student_career_goals")
    op.drop_table("learning_resources")
    bind = op.get_bind()
    for name in ("planitemstatus", "planitemkind", "planstatus"):
        sa.Enum(name=name).drop(bind, checkfirst=True)
