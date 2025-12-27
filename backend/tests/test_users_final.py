"""
Final Users Coverage Tests (Simplified)
Focus on logic that doesn't require complex DB session mocking.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.api.v1.users import get_current_user_info


@pytest.fixture
def mock_user():
    u = MagicMock()
    u.id = uuid4()
    u.username = "test"
    u.email = "test@example.com"
    return u


@pytest.mark.asyncio
async def test_get_current_user_info_simple(mock_user):
    """简单获取用户信息"""
    res = await get_current_user_info(mock_user)
    assert res == mock_user
