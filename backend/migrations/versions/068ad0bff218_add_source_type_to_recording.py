"""add_source_type_to_recording

Revision ID: 068ad0bff218
Revises: e135360ad0f7
Create Date: 2025-12-24 16:29:10.046146

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "068ad0bff218"
down_revision: str | Sequence[str] | None = "e135360ad0f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add source_type column with default value for existing records
    op.add_column("recordings", sa.Column("source_type", sa.String(length=20), nullable=True))

    # Set default value for existing records (assume they are realtime)
    op.execute("UPDATE recordings SET source_type = 'realtime' WHERE source_type IS NULL")

    # Now make it NOT NULL using batch mode for SQLite support
    with op.batch_alter_table("recordings") as batch_op:
        batch_op.alter_column(
            "source_type",
            existing_type=sa.String(length=20),
            nullable=False,
            server_default="realtime",
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("recordings", "source_type")
