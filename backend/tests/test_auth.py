"""
认证 API 测试
Test authentication endpoints
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_register_success():
    """验证：注册成功"""
    from app.api.v1.auth import register
    from app.schemas.user import UserRegister

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # No existing user
    mock_db.execute.return_value = mock_result

    user_data = UserRegister(email="test@example.com", username="testuser", password="password123")

    with patch("app.api.v1.auth.get_password_hash", return_value="hashed"):
        await register(user_data, mock_db)

    mock_db.add.assert_called()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_register_duplicate_email():
    """验证：重复邮箱注册失败"""
    from app.api.v1.auth import register
    from app.schemas.user import UserRegister

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock()  # Existing user
    mock_db.execute.return_value = mock_result

    user_data = UserRegister(
        email="existing@example.com", username="testuser", password="password123"
    )

    with pytest.raises(HTTPException) as exc_info:
        await register(user_data, mock_db)

    assert exc_info.value.status_code == 400
    assert "already registered" in exc_info.value.detail


@pytest.mark.asyncio
async def test_login_success():
    """验证：登录成功"""
    from app.api.v1.auth import login
    from app.schemas.user import UserLogin

    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_user.password_hash = "hashed_password"
    mock_user.is_active = True
    mock_user.role = "user"

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_result

    credentials = UserLogin(username="testuser", password="password123")

    with patch("app.api.v1.auth.verify_password", return_value=True):
        with patch("app.api.v1.auth.create_access_token", return_value="access_token"):
            with patch("app.api.v1.auth.create_refresh_token", return_value="refresh_token"):
                result = await login(credentials, mock_db)

    assert result.access_token == "access_token"
    assert result.refresh_token == "refresh_token"


@pytest.mark.asyncio
async def test_login_wrong_password():
    """验证：密码错误登录失败"""
    from app.api.v1.auth import login
    from app.schemas.user import UserLogin

    mock_user = MagicMock()
    mock_user.password_hash = "hashed"

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_result

    credentials = UserLogin(username="testuser", password="wrong")

    with patch("app.api.v1.auth.verify_password", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            await login(credentials, mock_db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user():
    """验证：非活跃用户登录失败"""
    from app.api.v1.auth import login
    from app.schemas.user import UserLogin

    mock_user = MagicMock()
    mock_user.password_hash = "hashed"
    mock_user.is_active = False

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_result

    credentials = UserLogin(username="testuser", password="correct")

    with patch("app.api.v1.auth.verify_password", return_value=True):
        with pytest.raises(HTTPException) as exc_info:
            await login(credentials, mock_db)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_refresh_token_success():
    """验证：刷新 token 成功"""
    from app.api.v1.auth import refresh_token
    from app.schemas.user import TokenRefresh

    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_user.is_active = True
    mock_user.role = "user"

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_result

    token_data = TokenRefresh(refresh_token="valid_refresh_token")

    with patch("app.api.v1.auth.decode_token", return_value={"sub": "user-123", "type": "refresh"}):
        with patch("app.api.v1.auth.create_access_token", return_value="new_access"):
            with patch("app.api.v1.auth.create_refresh_token", return_value="new_refresh"):
                result = await refresh_token(token_data, mock_db)

    assert result.access_token == "new_access"
    assert result.refresh_token == "new_refresh"


@pytest.mark.asyncio
async def test_refresh_token_invalid():
    """验证：无效 refresh token 失败"""
    from app.api.v1.auth import refresh_token
    from app.schemas.user import TokenRefresh

    mock_db = AsyncMock()
    token_data = TokenRefresh(refresh_token="invalid_token")

    with patch("app.api.v1.auth.decode_token", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await refresh_token(token_data, mock_db)

    assert exc_info.value.status_code == 401
