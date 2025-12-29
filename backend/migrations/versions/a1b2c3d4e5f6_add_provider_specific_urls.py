"""add_provider_specific_urls

Revision ID: a1b2c3d4e5f6
Revises: d6987ce366cc
Create Date: 2025-12-28 02:26:01.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "d6987ce366cc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("user_configs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("llm_urls", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("stt_urls", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("tts_urls", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("user_configs", schema=None) as batch_op:
        batch_op.drop_column("tts_urls")
        batch_op.drop_column("stt_urls")
        batch_op.drop_column("llm_urls")
