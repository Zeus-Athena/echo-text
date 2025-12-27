"""
TTS Service 测试
Test text-to-speech functionality
"""

import os
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_tts_init_with_config():
    """验证：使用 config 初始化 TTS Service"""
    from app.services.tts_service import TTSService

    mock_config = MagicMock()
    mock_config.tts_provider = "edge"
    mock_config.tts_voice = "zh-CN-XiaoxiaoNeural"
    mock_config.tts_api_key = None
    mock_config.tts_base_url = None

    service = TTSService(mock_config)

    assert service.provider == "edge"
    assert service.voice == "zh-CN-XiaoxiaoNeural"


def test_tts_init_defaults():
    """验证：无 config 时使用默认值"""
    from app.services.tts_service import TTSService

    service = TTSService(None)

    assert service.provider is not None
    assert service.voice is not None


@pytest.mark.asyncio
async def test_synthesize_edge_tts():
    """验证：Edge TTS 合成"""
    from app.services.tts_service import TTSService

    mock_config = MagicMock()
    mock_config.tts_provider = "edge"
    mock_config.tts_voice = "zh-CN-XiaoxiaoNeural"
    mock_config.tts_api_key = None
    mock_config.tts_base_url = None

    service = TTSService(mock_config)

    # Mock 'edge_tts' module using sys.modules
    mock_edge_module = MagicMock()
    mock_communicate = MagicMock()
    mock_communicate.save = AsyncMock()
    mock_edge_module.Communicate.return_value = mock_communicate

    # Create a temp file with some content for the test to read
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(b"fake audio data")
        tmp_path = tmp.name

    try:
        with patch.dict(sys.modules, {"edge_tts": mock_edge_module}):
            with patch("tempfile.NamedTemporaryFile") as mock_tmp:
                mock_tmp.return_value.__enter__.return_value.name = tmp_path

                result = await service._synthesize_edge_tts("Hello", "zh-CN-XiaoxiaoNeural", 1.0)

                assert result == b"fake audio data"
                mock_communicate.save.assert_called_once()

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_synthesize_openai_tts():
    """验证：OpenAI TTS 合成"""
    from app.services.tts_service import TTSService

    mock_config = MagicMock()
    mock_config.tts_provider = "openai"
    mock_config.tts_voice = "alloy"
    mock_config.tts_api_key = "test-key"
    mock_config.tts_base_url = None

    service = TTSService(mock_config)

    # Mock openai module
    mock_openai_module = MagicMock()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = b"audio bytes"
    mock_client.audio.speech.create = AsyncMock(return_value=mock_response)
    mock_openai_module.AsyncOpenAI.return_value = mock_client

    with patch.dict(sys.modules, {"openai": mock_openai_module}):
        result = await service._synthesize_openai_tts("Hello", "alloy", 1.0)

    assert result == b"audio bytes"


@pytest.mark.asyncio
async def test_synthesize_openai_requires_key():
    """验证：OpenAI TTS 需要 API key"""
    from app.services.tts_service import TTSService

    mock_config = MagicMock()
    mock_config.tts_provider = "openai"
    mock_config.tts_voice = "alloy"
    mock_config.tts_api_key = None  # No key
    mock_config.tts_base_url = None

    service = TTSService(mock_config)

    with pytest.raises(ValueError) as exc_info:
        await service._synthesize_openai_tts("Hello", "alloy", 1.0)

    assert "API key" in str(exc_info.value)


def test_get_available_voices():
    """验证：获取可用语音列表"""
    from app.services.tts_service import TTSService

    voices = TTSService.get_available_voices()

    assert len(voices) > 0
    assert any(v["id"] == "zh-CN-XiaoxiaoNeural" for v in voices)
    assert any(v["id"] == "en-US-JennyNeural" for v in voices)


@pytest.mark.asyncio
async def test_get_tts_service():
    """验证：get_tts_service 工厂函数"""
    from app.services.tts_service import get_tts_service

    service = await get_tts_service(None)

    assert service is not None
