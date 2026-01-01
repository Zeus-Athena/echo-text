"""
LLM 翻译上下文测试
Test translation with context parameter
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_translate_with_context():
    """验证：翻译调用时传入上下文"""
    from app.services.llm_service import LLMService

    # Create mock service
    service = LLMService.__new__(LLMService)
    service.provider = "test"
    service.api_key = "test-key"
    service.base_url = "https://test.api"
    service.model = "test-model"
    service.client = AsyncMock()

    # Mock response
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "你好世界"
    mock_response.choices = [mock_choice]
    service.client.chat.completions.create.return_value = mock_response

    result = await service.translate(
        "Hello world", source_lang="en", target_lang="zh", context="Previous sentence here."
    )

    # Should return translation
    assert result == "你好世界"

    # Verify API was called
    service.client.chat.completions.create.assert_called_once()

    # Verify context was included in prompt
    call_args = service.client.chat.completions.create.call_args
    messages = call_args.kwargs.get("messages", [])
    system_msg = messages[0]["content"] if messages else ""
    assert "Previous sentence here" in system_msg


@pytest.mark.asyncio
async def test_translate_without_context():
    """验证：无上下文时正常翻译"""
    from app.services.llm_service import LLMService

    service = LLMService.__new__(LLMService)
    service.provider = "test"
    service.api_key = "test-key"
    service.base_url = "https://test.api"
    service.model = "test-model"
    service.client = AsyncMock()

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "你好世界"
    mock_response.choices = [mock_choice]
    service.client.chat.completions.create.return_value = mock_response

    result = await service.translate(
        "Hello world",
        source_lang="en",
        target_lang="zh",
        # No context parameter
    )

    assert result == "你好世界"

    # Verify context section is NOT in prompt
    call_args = service.client.chat.completions.create.call_args
    messages = call_args.kwargs.get("messages", [])
    system_msg = messages[0]["content"] if messages else ""
    assert "For context" not in system_msg


@pytest.mark.asyncio
async def test_translate_prompt_contains_rules():
    """验证：翻译 prompt 包含防止摘要的规则"""
    from app.services.llm_service import LLMService

    service = LLMService.__new__(LLMService)
    service.provider = "test"
    service.api_key = "test-key"
    service.base_url = "https://test.api"
    service.model = "test-model"
    service.client = AsyncMock()

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "翻译结果"
    mock_response.choices = [mock_choice]
    service.client.chat.completions.create.return_value = mock_response

    await service.translate("Test text", source_lang="en", target_lang="zh")

    call_args = service.client.chat.completions.create.call_args
    messages = call_args.kwargs.get("messages", [])
    system_msg = messages[0]["content"] if messages else ""

    # Should contain anti-summarization rules
    assert "<rules>" in system_msg
    assert "Do NOT skip" in system_msg
