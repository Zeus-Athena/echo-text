"""add missing columns

Revision ID: 01dbaf1b7a3d
Revises: 
Create Date: 2025-12-21 19:30:27.694378

这个迁移用于同步既有数据库的 schema。
使用 IF NOT EXISTS 确保对新旧数据库都安全。
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '01dbaf1b7a3d'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    """Upgrade schema - 添加缺失的列"""
    
    # 1. users.can_use_admin_key - 允许用户使用管理员 API Key
    if not column_exists('users', 'can_use_admin_key'):
        op.add_column('users', sa.Column(
            'can_use_admin_key', 
            sa.Boolean(), 
            nullable=False,
            server_default=sa.text('false')
        ))
    
    # 未来新增的列可以在这里添加...
    # if not column_exists('table', 'column'):
    #     op.add_column('table', sa.Column(...))


def downgrade() -> None:
    """Downgrade schema - 回滚添加的列"""
    if column_exists('users', 'can_use_admin_key'):
        op.drop_column('users', 'can_use_admin_key')
