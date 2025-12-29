"""add llm_siliconflowglobal_api_key

Revision ID: g7h8i9j0k1l2
Revises: a1b2c3d4e5f6
Create Date: 2024-12-29 01:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g7h8i9j0k1l2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add llm_siliconflowglobal_api_key column
    op.add_column('user_configs', sa.Column('llm_siliconflowglobal_api_key', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove llm_siliconflowglobal_api_key column
    op.drop_column('user_configs', 'llm_siliconflowglobal_api_key')
