"""
LLM Service 测试
Test LLM translation and summary functionality
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_llm_init_with_config():
    """验证：使用 config 初始化 LLM Service"""
    from app.services.llm_service import LLMService

    mock_config = MagicMock()
    mock_config.llm_provider = "OpenAI"
    mock_config.llm_api_key = "test-key"
    mock_config.llm_openai_api_key = "openai-key"
    mock_config.llm_siliconflow_api_key = None
    mock_config.llm_base_url = "https://api.openai.com/v1"
    mock_config.llm_model = "gpt-4"

    service = LLMService(mock_config)

    # 逻辑：非 Groq/SiliconFlow 时，使用 llm_api_key
    assert service.api_key == "test-key"
    assert service.model == "gpt-4"


def test_llm_init_defaults():
    """验证：无 config 时使用默认值"""
    from app.services.llm_service import LLMService

    service = LLMService(None)

    # Should use settings defaults
    assert service.model is not None


@pytest.mark.asyncio
async def test_translate_basic():
    """验证：基本翻译功能"""
    from app.services.llm_service import LLMService

    mock_config = MagicMock()
    mock_config.llm_provider = "OpenAI"
    mock_config.llm_api_key = "key"
    mock_config.llm_openai_api_key = "key"
    mock_config.llm_siliconflow_api_key = None
    mock_config.llm_base_url = None
    mock_config.llm_model = "gpt-4"

    service = LLMService(mock_config)

    # Mock the OpenAI client
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="翻译结果"))]

    with patch.object(service, "client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await service.translate("Hello world", "en", "zh")

    assert result == "翻译结果"


@pytest.mark.asyncio
async def test_translate_with_context():
    """验证：带上下文的翻译"""
    from app.services.llm_service import LLMService

    mock_config = MagicMock()
    mock_config.llm_provider = "OpenAI"
    mock_config.llm_api_key = "key"
    mock_config.llm_openai_api_key = "key"
    mock_config.llm_siliconflow_api_key = None
    mock_config.llm_base_url = None
    mock_config.llm_model = "gpt-4"

    service = LLMService(mock_config)

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="上下文翻译"))]

    with patch.object(service, "client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await service.translate(
            "This is a test", "en", "zh", context="Previous sentence here"
        )

    assert result == "上下文翻译"


@pytest.mark.asyncio
async def test_api_error_handling():
    """验证：API 错误处理"""
    from app.services.llm_service import LLMService

    mock_config = MagicMock()
    mock_config.llm_provider = "OpenAI"
    mock_config.llm_api_key = "key"
    mock_config.llm_openai_api_key = "key"
    mock_config.llm_siliconflow_api_key = None
    mock_config.llm_base_url = None
    mock_config.llm_model = "gpt-4"

    service = LLMService(mock_config)

    with patch.object(service, "client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))

        with pytest.raises(Exception):  # noqa: B017
            await service.translate("Test", "en", "zh")


@pytest.mark.asyncio
async def test_get_llm_service():
    """验证：get_llm_service 工厂函数"""
    from app.services.llm_service import get_llm_service

    service = await get_llm_service(None)

    assert service is not None
