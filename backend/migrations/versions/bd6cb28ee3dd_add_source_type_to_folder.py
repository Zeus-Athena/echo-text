"""add_source_type_to_folder

Revision ID: bd6cb28ee3dd
Revises: 068ad0bff218
Create Date: 2025-12-24 18:38:18.092818

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bd6cb28ee3dd"
down_revision: str | Sequence[str] | None = "068ad0bff218"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add source_type column as nullable first
    op.add_column("folders", sa.Column("source_type", sa.String(length=20), nullable=True))

    # 2. Update existing folders to 'realtime'
    op.execute("UPDATE folders SET source_type = 'realtime' WHERE source_type IS NULL")

    # 3. Alter column to be NOT NULL with default 'realtime'
    with op.batch_alter_table("folders") as batch_op:
        batch_op.alter_column(
            "source_type",
            existing_type=sa.String(length=20),
            nullable=False,
            server_default="realtime",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("folders") as batch_op:
        batch_op.drop_column("source_type")
