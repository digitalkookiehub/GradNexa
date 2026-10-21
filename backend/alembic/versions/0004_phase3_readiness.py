"""phase 3: career roles, role skills, readiness rules, scores, skill gaps

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
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
        "career_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_ts(),
        _college_fk(),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("college_id", "name", name="uq_career_roles_college_name"),
    )
    op.create_index("ix_career_roles_college_id", "career_roles", ["college_id"])
    op.create_index("ix_career_roles_department_id", "career_roles", ["department_id"])

    op.create_table(
        "role_skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("required_level", sa.Numeric(5, 2), nullable=False),
        sa.Column("weight", sa.Numeric(5, 2), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["role_id"], ["career_roles.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("role_id", "skill_id", name="uq_role_skills_role_skill"),
        sa.CheckConstraint(
            "required_level >= 0 AND required_level <= 100", name="ck_role_skills_required_level"
        ),
        sa.CheckConstraint("weight > 0", name="ck_role_skills_weight"),
    )
    op.create_index("ix_role_skills_role_id", "role_skills", ["role_id"])
    op.create_index("ix_role_skills_college_id", "role_skills", ["college_id"])
    op.create_index("ix_role_skills_skill_id", "role_skills", ["skill_id"])

    op.create_table(
        "readiness_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("level_thresholds", sa.JSON(), nullable=False),
        sa.Column("gap_thresholds", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        *_ts(),
        _college_fk(),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("college_id", "version", name="uq_readiness_rules_college_version"),
    )
    op.create_index("ix_readiness_rules_college_id", "readiness_rules", ["college_id"])
    op.create_index("ix_readiness_rules_created_by", "readiness_rules", ["created_by"])

    op.create_table(
        "readiness_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=True),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("rule_version", sa.Integer(), nullable=False),
        sa.Column("overall", sa.Numeric(5, 2), nullable=True),
        sa.Column("level", sa.String(50), nullable=True),
        sa.Column("coverage", sa.Numeric(5, 2), nullable=False),
        sa.Column("category_scores", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column(
            "computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        *_ts(),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.ForeignKeyConstraint(["role_id"], ["career_roles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rule_id"], ["readiness_rules.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_readiness_scores_student_id", "readiness_scores", ["student_id"])
    op.create_index("ix_readiness_scores_college_id", "readiness_scores", ["college_id"])
    op.create_index("ix_readiness_scores_role_id", "readiness_scores", ["role_id"])
    op.create_index("ix_readiness_scores_rule_id", "readiness_scores", ["rule_id"])
    op.create_index(
        "ix_readiness_scores_student_role_computed",
        "readiness_scores",
        ["student_id", "role_id", "computed_at"],
    )

    op.create_table(
        "skill_gaps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("readiness_score_id", sa.Integer(), nullable=False),
        sa.Column("current", sa.Numeric(5, 2), nullable=True),
        sa.Column("required", sa.Numeric(5, 2), nullable=False),
        sa.Column("gap", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "status",
            sa.Enum("READY", "GAP", "NO_EVIDENCE", name="gapstatus"),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum("NONE", "LOW", "MEDIUM", "HIGH", "UNASSESSED", name="gappriority"),
            nullable=False,
        ),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column(
            "computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        *_ts(),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.ForeignKeyConstraint(["role_id"], ["career_roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["readiness_score_id"], ["readiness_scores.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_skill_gaps_student_id", "skill_gaps", ["student_id"])
    op.create_index("ix_skill_gaps_college_id", "skill_gaps", ["college_id"])
    op.create_index("ix_skill_gaps_role_id", "skill_gaps", ["role_id"])
    op.create_index("ix_skill_gaps_skill_id", "skill_gaps", ["skill_id"])
    op.create_index("ix_skill_gaps_readiness_score_id", "skill_gaps", ["readiness_score_id"])


def downgrade() -> None:
    op.drop_table("skill_gaps")
    op.drop_table("readiness_scores")
    op.drop_table("readiness_rules")
    op.drop_table("role_skills")
    op.drop_table("career_roles")
    bind = op.get_bind()
    for name in ("gappriority", "gapstatus"):
        sa.Enum(name=name).drop(bind, checkfirst=True)
