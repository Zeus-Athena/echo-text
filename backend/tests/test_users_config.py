"""
User Config & Management 测试
Test user configuration and admin operations
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = uuid4()
    user.role = "user"
    user.config = MagicMock()

    # Initialize all potential fields to avoid MagicMock pollution and validation errors
    user.config.llm_provider = "openai"
    user.config.llm_model = "gpt-4"
    user.config.llm_api_key = "sk-..."
    user.config.llm_base_url = None
    user.config.llm_groq_api_key = None
    user.config.llm_siliconflow_api_key = None

    user.config.tts_provider = "edge"
    user.config.tts_voice = "zh-CN-XiaoxiaoNeural"
    user.config.tts_api_key = None
    user.config.tts_base_url = None

    user.config.stt_provider = "openai"
    user.config.stt_api_key = None
    user.config.stt_base_url = None
    user.config.stt_model = "whisper-1"
    user.config.stt_groq_api_key = None
    user.config.stt_deepgram_api_key = None
    user.config.stt_openai_api_key = None
    user.config.stt_siliconflow_api_key = None

    user.config.dict_provider = "youdao"
    user.config.dict_api_key = None

    user.config.theme = "light"
    user.config.default_source_lang = "en"
    user.config.default_target_lang = "zh"

    user.config.audio_buffer_duration = 6.0
    user.config.silence_threshold = 500
    user.config.silence_mode = "vad"
    user.config.silence_prefer_source = "mic"
    user.config.silence_threshold_source = "mic"

    return user


@pytest.fixture
def mock_admin():
    admin = MagicMock()
    admin.id = uuid4()
    admin.role = "admin"
    return admin


@pytest.fixture
def mock_db():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result
    return db


@pytest.mark.asyncio
async def test_get_user_config(mock_user, mock_db):
    """验证：获取用户配置"""
    from app.api.v1.users import get_user_config

    # Ensure config query returns user's config
    async def mock_execute(query):
        m = MagicMock()
        m.scalar_one_or_none.return_value = mock_user.config
        return m

    mock_db.execute.side_effect = mock_execute

    response = await get_user_config(mock_user, mock_db)

    assert response.llm.model == "gpt-4"
    assert "zh-CN" in response.tts.voice
    # API key should be masked
    assert "***" in response.llm.api_key


@pytest.mark.asyncio
async def test_update_user_config(mock_user, mock_db):
    """验证：更新用户配置"""
    from app.api.v1.users import update_user_config
    from app.schemas.user import LLMConfig, UserConfigUpdate

    update_data = UserConfigUpdate(llm=LLMConfig(model="claude-3"))

    # Mock config retrieval
    async def mock_execute(query):
        m = MagicMock()
        m.scalar_one_or_none.return_value = mock_user.config
        return m

    mock_db.execute.side_effect = mock_execute

    await update_user_config(update_data, mock_user, mock_db)

    # We don't check response content strictly here as we just want to ensure update flow works
    mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_list_users_admin_only(mock_admin, mock_user, mock_db):
    """验证：管理员列出用户"""
    from app.api.v1.users import list_users

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_user]
    mock_db.execute.return_value = mock_result

    users = await list_users(mock_admin, mock_db)

    assert len(users) == 1
    assert users[0].id == mock_user.id


@pytest.mark.asyncio
async def test_create_user_admin(mock_admin, mock_db):
    """验证：管理员创建用户"""
    from app.api.v1.users import create_user
    from app.schemas.user import AdminCreateUser

    data = AdminCreateUser(
        email="new@example.com", username="newuser", password="password123", role="user"
    )

    # Check duplicate
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.MonkeyPatch.context() as m:
        m.setattr("app.api.v1.users.get_password_hash", lambda p: "hashed")

        # Mock user creation
        def mock_add(obj):
            if hasattr(obj, "email"):  # User object
                obj.id = uuid4()

        mock_db.add.side_effect = mock_add

        result = await create_user(data, mock_admin, mock_db)

    assert mock_db.add.call_count >= 2  # User + Config
    mock_db.commit.assert_called()
    assert result.email == "new@example.com"


@pytest.mark.asyncio
async def test_delete_user_admin(mock_admin, mock_db):
    """验证：管理员删除用户"""
    from app.api.v1.users import delete_user

    target_id = str(uuid4())
    mock_target = MagicMock()
    mock_target.id = target_id

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_target
    mock_db.execute.return_value = mock_result

    await delete_user(target_id, mock_admin, mock_db)

    mock_db.delete.assert_called_with(mock_target)
    mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_delete_user_not_found(mock_admin, mock_db):
    """验证：删除不存在的用户报错"""
    from app.api.v1.users import delete_user

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc:
        await delete_user(str(uuid4()), mock_admin, mock_db)

    assert exc.value.status_code == 404
