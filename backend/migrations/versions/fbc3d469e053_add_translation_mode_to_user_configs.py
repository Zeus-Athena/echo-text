"""add translation_mode to user_configs

Revision ID: fbc3d469e053
Revises: a888766a274e
Create Date: 2025-12-26 20:57:40.135054

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'fbc3d469e053'
down_revision: str | Sequence[str] | None = 'a888766a274e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('user_configs', sa.Column('translation_mode', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('user_configs', 'translation_mode')
