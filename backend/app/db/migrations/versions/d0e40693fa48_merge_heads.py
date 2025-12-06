"""merge heads

Revision ID: d0e40693fa48
Revises: 29fe1954e0b1, g123456789ab
Create Date: 2025-12-06 12:09:52.737516

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0e40693fa48'
down_revision: Union[str, Sequence[str], None] = ('29fe1954e0b1', 'g123456789ab')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
