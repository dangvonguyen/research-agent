"""add_query_to_crawler_job

Revision ID: g123456789ab
Revises: d7d9e7c73773
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g123456789ab'
down_revision: Union[str, Sequence[str], None] = 'd7d9e7c73773'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add query column to crawler_job table
    op.add_column('crawler_job', sa.Column('query', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove query column from crawler_job table
    op.drop_column('crawler_job', 'query')

