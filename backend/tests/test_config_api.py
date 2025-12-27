"""
Config API Tests
测试配置测试接口
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def mock_user():
    u = MagicMock()
    u.id = uuid4()
    return u


@pytest.fixture
def mock_db():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result
    return db


class TestGetSTTModels:
    """测试获取 STT 模型列表"""

    @pytest.mark.asyncio
    async def test_get_stt_models_returns_models_list(self, mock_user):
        """测试返回模型列表"""
        from app.api.v1.config import get_stt_models

        result = await get_stt_models(mock_user)

        assert "models" in result
        assert "recommended" in result
        assert result["recommended"] == "whisper-large-v3-turbo"
        assert len(result["models"]) > 0

    @pytest.mark.asyncio
    async def test_get_stt_models_contains_expected_providers(self, mock_user):
        """测试包含预期的提供商"""
        from app.api.v1.config import get_stt_models

        result = await get_stt_models(mock_user)

        providers = {m["provider"] for m in result["models"]}
        assert "GROQ" in providers
        assert "OpenAI" in providers
        assert "Deepgram" in providers

    @pytest.mark.asyncio
    async def test_get_stt_models_has_recommended_model(self, mock_user):
        """测试推荐模型存在"""
        from app.api.v1.config import get_stt_models

        result = await get_stt_models(mock_user)

        recommended = [m for m in result["models"] if m.get("recommended")]
        assert len(recommended) >= 1


class TestTestTTSConfig:
    """测试 TTS 配置测试"""

    @pytest.mark.asyncio
    async def test_tts_edge_provider(self, mock_user):
        """测试 Edge TTS 提供商"""
        from app.api.v1.config import test_tts_config
        from app.schemas.user import ConfigTestRequest

        request = ConfigTestRequest(
            provider="edge",
            api_key="not-needed",
            base_url="",
        )

        with patch("edge_tts.list_voices", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [{"Name": "voice1"}]
            result = await test_tts_config(request, mock_user)

        assert result.success is True
        assert "Edge TTS" in result.message
        assert result.provider == "edge"

    @pytest.mark.asyncio
    async def test_tts_openai_provider(self, mock_user):
        """测试 OpenAI TTS 提供商"""
        from app.api.v1.config import test_tts_config
        from app.schemas.user import ConfigTestRequest

        request = ConfigTestRequest(
            provider="openai",
            api_key="test-api-key",
            base_url="https://api.openai.com/v1",
        )

        with patch("openai.AsyncOpenAI"):
            result = await test_tts_config(request, mock_user)

        assert result.success is True
        assert "OpenAI TTS" in result.message

    @pytest.mark.asyncio
    async def test_tts_custom_provider(self, mock_user):
        """测试自定义 TTS 提供商"""
        from app.api.v1.config import test_tts_config
        from app.schemas.user import ConfigTestRequest

        request = ConfigTestRequest(
            provider="custom",
            api_key="test-key",
            base_url="https://custom.api.com",
        )

        result = await test_tts_config(request, mock_user)

        assert result.success is True
        assert "Custom TTS provider" in result.message


class TestTestLLMConfig:
    """测试 LLM 配置测试"""

    @pytest.mark.asyncio
    async def test_llm_config_success(self, mock_user, mock_db):
        """测试 LLM 配置成功"""
        from app.api.v1.config import test_llm_config
        from app.schemas.user import ConfigTestRequest

        request = ConfigTestRequest(
            provider="openai",
            api_key="test-api-key",
            base_url="https://api.openai.com/v1",
            model="gpt-3.5-turbo",
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello, test successful!"

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.models.list = AsyncMock(return_value=MagicMock())
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            result = await test_llm_config(request, mock_user, mock_db)

        assert result.success is True
        assert result.provider == "openai"
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_llm_config_masked_key_no_config(self, mock_user, mock_db):
        """测试使用掩码 API Key 但无有效配置"""
        from fastapi import HTTPException

        from app.api.v1.config import test_llm_config
        from app.schemas.user import ConfigTestRequest

        request = ConfigTestRequest(
            provider="openai",
            api_key="***",
            base_url="https://api.openai.com/v1",
        )

        with patch("app.api.v1.config.get_effective_config", new_callable=AsyncMock) as mock_cfg:
            mock_cfg.return_value = MagicMock(llm_api_key=None, llm_groq_api_key=None)

            with pytest.raises(HTTPException) as exc:
                await test_llm_config(request, mock_user, mock_db)

            assert exc.value.status_code == 400
            assert "API Key" in exc.value.detail


class TestTestSTTConfig:
    """测试 STT 配置测试"""

    @pytest.mark.asyncio
    async def test_stt_config_masked_key_no_config(self, mock_user, mock_db):
        """测试使用掩码 API Key 但无有效配置"""
        from fastapi import HTTPException

        from app.api.v1.config import test_stt_config
        from app.schemas.user import ConfigTestRequest

        request = ConfigTestRequest(
            provider="groq",
            api_key="***",
            base_url="https://api.groq.com/v1",
        )

        with patch("app.api.v1.config.get_effective_config", new_callable=AsyncMock) as mock_cfg:
            mock_cfg.return_value = MagicMock(stt_groq_api_key=None, stt_api_key=None)

            with pytest.raises(HTTPException) as exc:
                await test_stt_config(request, mock_user, mock_db)

            assert exc.value.status_code == 400
            assert "API Key" in exc.value.detail

    @pytest.mark.asyncio
    async def test_stt_config_success_with_models_list(self, mock_user, mock_db):
        """测试 STT 配置成功 - models.list 可用"""
        from app.api.v1.config import test_stt_config
        from app.schemas.user import ConfigTestRequest

        request = ConfigTestRequest(
            provider="openai",
            api_key="test-api-key",
            base_url="https://api.openai.com/v1",
        )

        mock_models = MagicMock()
        mock_models.data = [MagicMock(id="whisper-1"), MagicMock(id="whisper-2")]

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.models.list = AsyncMock(return_value=mock_models)
            mock_openai.return_value = mock_client

            result = await test_stt_config(request, mock_user, mock_db)

        assert result.success is True
        assert "STT 连接成功" in result.message


class TestFetchSTTModelsFromProvider:
    """测试从提供商获取模型列表"""

    @pytest.mark.asyncio
    async def test_fetch_models_success(self, mock_user, mock_db):
        """测试成功获取模型列表"""
        from app.api.v1.config import fetch_stt_models_from_provider
        from app.schemas.user import ConfigTestRequest

        request = ConfigTestRequest(
            provider="groq",
            api_key="test-api-key",
            base_url="https://api.groq.com/v1",
        )

        mock_models = MagicMock()
        mock_models.data = [
            MagicMock(id="whisper-large-v3-turbo"),
            MagicMock(id="whisper-large-v3"),
        ]

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.models.list = AsyncMock(return_value=mock_models)
            mock_openai.return_value = mock_client

            result = await fetch_stt_models_from_provider(request, mock_user, mock_db)

        assert "models" in result
        assert len(result["models"]) >= 1

    @pytest.mark.asyncio
    async def test_fetch_models_no_stt_models_returns_all(self, mock_user, mock_db):
        """测试无 STT 模型时返回所有模型"""
        from app.api.v1.config import fetch_stt_models_from_provider
        from app.schemas.user import ConfigTestRequest

        request = ConfigTestRequest(
            provider="custom",
            api_key="test-api-key",
            base_url="https://api.custom.com/v1",
        )

        mock_models = MagicMock()
        mock_models.data = [
            MagicMock(id="gpt-4"),
            MagicMock(id="gpt-3.5-turbo"),
        ]

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.models.list = AsyncMock(return_value=mock_models)
            mock_openai.return_value = mock_client

            result = await fetch_stt_models_from_provider(request, mock_user, mock_db)

        assert "models" in result
        # Should return non-STT models as fallback
        assert len(result["models"]) >= 1
