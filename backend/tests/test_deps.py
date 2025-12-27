"""
Tests for api/deps.py
API 依赖注入测试
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.deps import verify_token


class TestVerifyToken:
    """verify_token 测试"""

    def test_valid_token(self):
        """测试有效 token"""
        with patch("app.api.deps.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": "user123", "exp": 9999999999}

            result = verify_token("valid_token")

            assert result["sub"] == "user123"
            mock_decode.assert_called_once_with("valid_token")

    def test_invalid_token_raises(self):
        """测试无效 token 抛出异常"""
        with patch("app.api.deps.decode_token") as mock_decode:
            mock_decode.return_value = None

            with pytest.raises(ValueError, match="Invalid token"):
                verify_token("invalid_token")

    def test_expired_token_raises(self):
        """测试过期 token 抛出异常"""
        with patch("app.api.deps.decode_token") as mock_decode:
            mock_decode.return_value = None  # 过期返回 None

            with pytest.raises(ValueError, match="Invalid token"):
                verify_token("expired_token")


class TestGetCurrentUserMocked:
    """get_current_user 模拟测试"""

    @pytest.mark.asyncio
    async def test_missing_payload_sub(self):
        """测试缺少 sub 字段"""
        from app.api.deps import get_current_user

        mock_credentials = MagicMock()
        mock_credentials.credentials = "token_without_sub"
        mock_db = AsyncMock()

        with patch("app.api.deps.decode_token") as mock_decode:
            # 返回没有 sub 的 payload
            mock_decode.return_value = {"exp": 9999999999}

            with pytest.raises(HTTPException) as exc:
                await get_current_user(mock_credentials, mock_db)

            assert exc.value.status_code == 401
            assert "Invalid token payload" in exc.value.detail

    @pytest.mark.asyncio
    async def test_invalid_token(self):
        """测试无效 token"""
        from app.api.deps import get_current_user

        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid_token"
        mock_db = AsyncMock()

        with patch("app.api.deps.decode_token") as mock_decode:
            mock_decode.return_value = None

            with pytest.raises(HTTPException) as exc:
                await get_current_user(mock_credentials, mock_db)

            assert exc.value.status_code == 401


class TestGetCurrentActiveUserMocked:
    """get_current_active_user 模拟测试"""

    @pytest.mark.asyncio
    async def test_active_user(self):
        """测试活跃用户"""
        from app.api.deps import get_current_active_user

        mock_user = MagicMock()
        mock_user.is_active = True

        result = await get_current_active_user(mock_user)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_inactive_user_raises(self):
        """测试非活跃用户"""
        from app.api.deps import get_current_active_user

        mock_user = MagicMock()
        mock_user.is_active = False

        with pytest.raises(HTTPException) as exc:
            await get_current_active_user(mock_user)

        assert exc.value.status_code == 403
        assert "Inactive" in exc.value.detail


class TestGetAdminUserMocked:
    """get_admin_user 模拟测试"""

    @pytest.mark.asyncio
    async def test_admin_user(self):
        """测试管理员用户"""
        from app.api.deps import get_admin_user

        mock_user = MagicMock()
        mock_user.role = "admin"

        result = await get_admin_user(mock_user)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_non_admin_user_raises(self):
        """测试非管理员用户"""
        from app.api.deps import get_admin_user

        mock_user = MagicMock()
        mock_user.role = "user"

        with pytest.raises(HTTPException) as exc:
            await get_admin_user(mock_user)

        assert exc.value.status_code == 403
        assert "Admin" in exc.value.detail


class TestGetOptionalUser:
    """get_optional_user 测试"""

    def test_no_credentials(self):
        """测试没有凭证"""
        from app.api.deps import get_optional_user

        mock_db = MagicMock()
        result = get_optional_user(None, mock_db)

        assert result is None

    def test_with_credentials_invalid_token(self):
        """测试凭证无效 token"""
        from app.api.deps import get_optional_user

        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid"
        mock_db = MagicMock()

        with patch("app.api.deps.decode_token") as mock_decode:
            mock_decode.return_value = None

            result = get_optional_user(mock_credentials, mock_db)

            assert result is None
