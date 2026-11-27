"""Add threshold column to predictions table

Revision ID: 0002_add_threshold
Revises: 0001_initial_tables
Create Date: 2026-11-27 19:57:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_add_threshold'
down_revision: Union[str, None] = '0001_initial_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'predictions',
        sa.Column('threshold', sa.Float(), server_default='0.5', nullable=False)
    )


def downgrade() -> None:
    op.drop_column('predictions', 'threshold')
