"""Migrate to JSONB content

Revision ID: 29fe1954e0b1
Revises: 9aacc8ee6a2d
Create Date: 2025-12-03 13:52:49.888886

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "29fe1954e0b1"
down_revision: Union[str, Sequence[str], None] = "9aacc8ee6a2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Add a new column for JSON content
    op.add_column(
        "message", sa.Column("content_json", postgresql.JSONB(), nullable=True)
    )

    # Step 2: Migrate existing data from String to JSON format
    op.execute("""
        UPDATE message
        SET content_json = json_build_array(
            json_build_object('type', 'text', 'text', content)
        )
    """)

    # Step 3: Drop the old content column
    op.drop_column("message", "content")

    # Step 4: Rename content_json to content
    op.alter_column("message", "content_json", new_column_name="content")

    # Step 5: Make the column NOT NULL
    op.alter_column("message", "content", nullable=False)

    # Add GIN index for efficient tool call queries
    op.create_index(
        "ix_message_content_tool_calls",
        "message",
        ["content"],
        postgresql_using="gin",
        postgresql_ops={"content": "jsonb_path_ops"},
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Step 1: Add a temporary string column
    op.add_column("message", sa.Column("content_text", sa.String(), nullable=True))

    # Step 2: Extract text from first text part in JSON
    op.execute("""
        UPDATE message
        SET content_text = content->0->>'text'
        WHERE content IS NOT NULL
    """)

    # Step 3: Drop the JSON content column
    op.drop_column("message", "content")

    # Step 4: Rename content_text to content
    op.alter_column("message", "content_text", new_column_name="content")

    # Step 5: Make the column NOT NULL
    op.alter_column("message", "content", nullable=False)

    # Drop GIN index
    op.drop_index("ix_message_content_tool_calls", table_name="message")
