"""
Simulated Streaming Processor Tests (Fixed)
Cover elastic window logic, VAD check, and text validation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.audio_processors.base import ProcessorConfig
from app.services.audio_processors.simulated import SimulatedStreamingProcessor


@pytest.fixture
def mock_config():
    return ProcessorConfig(
        provider="openai",
        model="whisper-1",
        source_lang="en",
        target_lang="zh",
        buffer_duration=6.0,
        silence_threshold=30.0,
    )


@pytest.fixture
def mock_stt():
    stt = MagicMock()
    stt.transcribe = AsyncMock(return_value={"text": "Hello world", "segments": []})
    return stt


@pytest.fixture
def processor(mock_config, mock_stt):
    return SimulatedStreamingProcessor(config=mock_config, stt_service=mock_stt)


def test_is_valid_text(processor):
    """测试幻觉过滤逻辑"""
    assert processor._is_valid_text("Hello world, this is a test.") == True
    assert processor._is_valid_text("Hi") == False
    assert processor._is_valid_text("...") == False
    assert processor._is_valid_text("thank you.") == False
    assert processor._is_valid_text("谢谢。") == False


@pytest.mark.asyncio
async def test_on_start(processor):
    """测试启动初始化"""
    with patch("app.services.audio_processors.simulated.get_vad_service") as mock_vad:
        mock_vad_instance = MagicMock()
        mock_vad.return_value = mock_vad_instance

        await processor._on_start()

        assert processor._stt_last_index == 0
        mock_vad_instance.reset_states.assert_called_once()


@pytest.mark.asyncio
async def test_on_stop(processor):
    """测试停止时处理剩余音频"""
    processor._all_audio_chunks = [b"chunk1", b"chunk2"]
    processor._stt_last_index = 0

    with patch.object(processor, "_send_for_transcription", new_callable=AsyncMock) as mock_send:
        await processor._on_stop()
        mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_process_chunk_phase1(processor):
    """Phase 1 - 未达到 min_chunks"""
    processor._stt_last_index = 0
    processor._all_audio_chunks = [b"c"] * 3

    with patch.object(processor, "_send_for_transcription", new_callable=AsyncMock) as mock_send:
        await processor._process_chunk(b"new")
        mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_process_chunk_phase3(processor):
    """Phase 3 - 达到 max_chunks 强制发送"""
    processor._stt_last_index = 0
    processor._all_audio_chunks = [b"c"] * 30
    processor._header_chunk = b"header"

    with patch.object(processor, "_send_for_transcription", new_callable=AsyncMock) as mock_send:
        await processor._process_chunk(b"new")
        mock_send.assert_called_once()
