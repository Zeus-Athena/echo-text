"""add_translation_burst

Revision ID: 4c1125a3ceeb
Revises: 787cacb89a44
Create Date: 2025-12-31 14:47:55.275692

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c1125a3ceeb"
down_revision: str | Sequence[str] | None = "787cacb89a44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add translation_burst column to user_configs
    op.add_column(
        "user_configs",
        sa.Column("translation_burst", sa.Integer(), nullable=True, server_default="10"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user_configs", "translation_burst")
