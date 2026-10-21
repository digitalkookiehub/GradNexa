"""phase 8: rag documents, rag chunks, mcp tools, hod assignments

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
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
        "rag_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum(
                "SYLLABUS",
                "CURRICULUM",
                "LEARNING_MATERIAL",
                "PLACEMENT_GUIDE",
                "INTERVIEW_GUIDE",
                "POLICY",
                "OTHER",
                name="ragsourcetype",
            ),
            nullable=False,
        ),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "APPROVED", "ARCHIVED", name="ragdocumentstatus"),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        *_ts(),
        _college_fk(),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("storage_key", name="uq_rag_documents_storage_key"),
    )
    op.create_index("ix_rag_documents_college_id", "rag_documents", ["college_id"])
    op.create_index("ix_rag_documents_department_id", "rag_documents", ["department_id"])
    op.create_index("ix_rag_documents_uploaded_by", "rag_documents", ["uploaded_by"])
    op.create_index("ix_rag_documents_approved_by", "rag_documents", ["approved_by"])
    op.create_index("ix_rag_documents_college_status", "rag_documents", ["college_id", "status"])

    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("chunk_metadata", sa.JSON(), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(["document_id"], ["rag_documents.id"], ondelete="CASCADE"),
        _college_fk(),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_rag_chunks_document_chunk"),
        sa.CheckConstraint("chunk_index >= 0", name="ck_rag_chunks_chunk_index"),
    )
    op.create_index("ix_rag_chunks_college_id", "rag_chunks", ["college_id"])

    op.create_table(
        "mcp_tools",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_ts(),
        _college_fk(),
        sa.UniqueConstraint("college_id", "name", name="uq_mcp_tools_college_name"),
    )

    op.create_table(
        "hod_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("college_id", sa.Integer(), nullable=False),
        sa.Column("hod_user_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        *_ts(),
        _college_fk(),
        sa.ForeignKeyConstraint(["hod_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("hod_user_id", "department_id", name="uq_hod_assignments_user_dept"),
    )
    op.create_index("ix_hod_assignments_college_id", "hod_assignments", ["college_id"])
    op.create_index("ix_hod_assignments_department_id", "hod_assignments", ["department_id"])


def downgrade() -> None:
    op.drop_table("hod_assignments")
    op.drop_table("mcp_tools")
    op.drop_table("rag_chunks")
    op.drop_table("rag_documents")
    bind = op.get_bind()
    sa.Enum(name="ragdocumentstatus").drop(bind, checkfirst=True)
    sa.Enum(name="ragsourcetype").drop(bind, checkfirst=True)
