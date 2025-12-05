"""Migrate attachment storage from a separate table to JSONB fields

Revision ID: 9aacc8ee6a2d
Revises: abb7f48dfa56
Create Date: 2025-12-03 10:17:53.442247

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9aacc8ee6a2d"
down_revision: Union[str, Sequence[str], None] = "abb7f48dfa56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f("ix_attachment_message_created_at"), table_name="attachment")
    op.drop_index(op.f("ix_attachment_message_id"), table_name="attachment")
    op.drop_table("attachment")
    op.add_column(
        "message",
        sa.Column(
            "attachments", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("message", "attachments")
    op.create_table(
        "attachment",
        sa.Column("id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column("filename", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("content_type", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("path", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("size", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("message_id", sa.UUID(), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["message.id"],
            name=op.f("attachment_message_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("attachment_pkey")),
    )
    op.create_index(
        op.f("ix_attachment_message_id"), "attachment", ["message_id"], unique=False
    )
    op.create_index(
        op.f("ix_attachment_message_created_at"),
        "attachment",
        ["message_id", "created_at"],
        unique=False,
    )
