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


@pytest.mark.asyncio
async def test_translate_prompt_contains_no_skip_rules():
    """验证：翻译 prompt 包含禁止省略内容的规则"""
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
    mock_response.choices = [MagicMock(message=MagicMock(content="翻译结果"))]

    captured_messages = []

    async def capture_call(*args, **kwargs):
        captured_messages.append(kwargs.get("messages", []))
        return mock_response

    with patch.object(service, "client") as mock_client:
        mock_client.chat.completions.create = capture_call

        await service.translate("Hello world. How are you?", "en", "zh")

    # 验证 system prompt 包含关键规则
    assert len(captured_messages) == 1
    system_prompt = captured_messages[0][0]["content"]
    # Update assertions to check for XML tags and new structure
    assert "<rules>" in system_prompt
    assert "Do NOT skip" in system_prompt
    assert "EVERY SINGLE sentence" in system_prompt
    assert "SAME number of sentences" in system_prompt


@pytest.mark.asyncio
async def test_translate_stream_prompt_contains_no_skip_rules():
    """验证：流式翻译 prompt 包含禁止省略内容的规则"""
    from app.services.llm_service import LLMService

    mock_config = MagicMock()
    mock_config.llm_provider = "OpenAI"
    mock_config.llm_api_key = "key"
    mock_config.llm_openai_api_key = "key"
    mock_config.llm_siliconflow_api_key = None
    mock_config.llm_base_url = None
    mock_config.llm_model = "gpt-4"

    service = LLMService(mock_config)

    # Mock stream response
    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock(delta=MagicMock(content="Chunk"))]
    
    # Create an async iterator for the stream
    async def async_stream():
        yield mock_chunk

    captured_messages = []

    async def capture_call(*args, **kwargs):
        captured_messages.append(kwargs.get("messages", []))
        return async_stream()

    with patch.object(service, "client") as mock_client:
        mock_client.chat.completions.create = capture_call

        # Consume the stream
        async for _ in service.translate_stream("Hello", "en", "zh"):
            pass

    # 验证 system prompt
    assert len(captured_messages) == 1
    system_prompt = captured_messages[0][0]["content"]
    # Update assertions for streaming prompt
    assert "<rules>" in system_prompt
    assert "Do NOT skip" in system_prompt
