"""phase 0 initial: colleges, users, tokens, audit logs

Revision ID: 0001
Revises:
Create Date: 2026-10-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TS = dict(server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "colleges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), **TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), **TS),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "STUDENT", "FACULTY", "TPO", "HOD", "ADMIN", "SUPER_ADMIN",
                name="userrole",
            ),
            server_default="STUDENT",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), **TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), **TS),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_users_college_id", "users", ["college_id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    for table, flag in (("refresh_tokens", "revoked"), ("password_reset_tokens", "used")):
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.String(128), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(flag, sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), **TS),
            sa.Column("updated_at", sa.DateTime(timezone=True), **TS),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])
        op.create_index(f"ix_{table}_token_hash", table, ["token_hash"], unique=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("college_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), **TS),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_logs_college_id", "audit_logs", ["college_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("password_reset_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.drop_table("colleges")
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
