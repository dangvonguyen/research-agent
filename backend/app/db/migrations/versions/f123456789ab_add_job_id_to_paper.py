"""add job_id to paper

Revision ID: f123456789ab
Revises: e840e1cb1ca9
Create Date: 2025-11-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f123456789ab"
down_revision: Union[str, Sequence[str], None] = "e840e1cb1ca9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "paper",
        sa.Column("job_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        op.f("ix_paper_job_id"),
        "paper",
        ["job_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_paper_job_id_crawler_job",
        source_table="paper",
        referent_table="crawler_job",
        local_cols=["job_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_paper_job_id_crawler_job",
        "paper",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_paper_job_id"), table_name="paper")
    op.drop_column("paper", "job_id")


