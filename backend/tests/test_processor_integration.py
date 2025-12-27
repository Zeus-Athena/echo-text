"""
Integration Tests for ws_v2 WebSocket Endpoint
测试新架构 WebSocket 端点的集成
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.audio_processors.base import ProcessorConfig, TranscriptEvent
from app.services.audio_processors.simulated import SimulatedStreamingProcessor


class TestProcessorCallbacks:
    """测试处理器回调机制"""

    @pytest.mark.asyncio
    async def test_on_transcript_callback_called(self):
        """on_transcript 回调应该被正确调用"""
        callback_results = []

        async def on_transcript(event: TranscriptEvent):
            callback_results.append(event)

        config = ProcessorConfig(provider="Groq", model="test")
        mock_stt_service = MagicMock()

        processor = SimulatedStreamingProcessor(
            config=config,
            stt_service=mock_stt_service,
            on_transcript=on_transcript,
        )

        # Simulate emitting a transcript
        await processor._emit_transcript(
            TranscriptEvent(
                text="Hello World",
                is_final=True,
            )
        )

        assert len(callback_results) == 1
        assert callback_results[0].text == "Hello World"
        assert callback_results[0].is_final is True

    @pytest.mark.asyncio
    async def test_on_error_callback_called(self):
        """on_error 回调应该被正确调用"""
        error_messages = []

        async def on_error(message: str):
            error_messages.append(message)

        config = ProcessorConfig(provider="Groq", model="test")
        mock_stt_service = MagicMock()

        processor = SimulatedStreamingProcessor(
            config=config,
            stt_service=mock_stt_service,
            on_error=on_error,
        )

        await processor._emit_error("Test error message")

        assert len(error_messages) == 1
        assert error_messages[0] == "Test error message"

    @pytest.mark.asyncio
    async def test_callback_exception_does_not_crash(self):
        """回调异常不应该导致处理器崩溃"""

        async def bad_callback(event: TranscriptEvent):
            raise Exception("Callback error")

        config = ProcessorConfig(provider="Groq", model="test")
        mock_stt_service = MagicMock()

        processor = SimulatedStreamingProcessor(
            config=config,
            stt_service=mock_stt_service,
            on_transcript=bad_callback,
        )

        # Should not raise
        await processor._emit_transcript(TranscriptEvent(text="Test"))


class TestAudioPersistenceGuarantee:
    """测试音频持久化保障"""

    @pytest.mark.asyncio
    async def test_all_chunks_saved_on_stop(self):
        """停止时应该返回所有音频块"""
        config = ProcessorConfig(provider="Groq", model="test")
        mock_stt_service = MagicMock()
        mock_stt_service.transcribe = AsyncMock(return_value={"text": ""})

        processor = SimulatedStreamingProcessor(
            config=config,
            stt_service=mock_stt_service,
        )

        await processor.start()

        # 发送多个音频块
        chunks = [b"chunk1", b"chunk2", b"chunk3", b"chunk4", b"chunk5"]
        for chunk in chunks:
            await processor.process_audio(chunk)

        header, data = await processor.stop()

        # 验证所有块都被保存
        for chunk in chunks:
            assert chunk in data

    @pytest.mark.asyncio
    async def test_header_chunk_preserved(self):
        """WebM 头部块应该被正确保存"""
        config = ProcessorConfig(provider="Groq", model="test")
        mock_stt_service = MagicMock()
        mock_stt_service.transcribe = AsyncMock(return_value={"text": ""})

        processor = SimulatedStreamingProcessor(
            config=config,
            stt_service=mock_stt_service,
        )

        await processor.start()

        header_data = b"WEBM_HEADER"
        await processor.process_audio(header_data)
        await processor.process_audio(b"audio_data")

        header, data = await processor.stop()

        assert header == header_data


class TestTranscriptEventFormat:
    """测试转录事件格式"""

    def test_event_with_speaker(self):
        """事件应该支持说话人标签"""
        event = TranscriptEvent(
            text="Hello",
            is_final=True,
            speaker="Speaker 1",
        )
        assert event.speaker == "Speaker 1"

    def test_event_with_timestamps(self):
        """事件应该支持时间戳"""
        event = TranscriptEvent(
            text="Hello",
            start_time=1.5,
            end_time=3.0,
        )
        assert event.start_time == 1.5
        assert event.end_time == 3.0

    def test_event_with_confidence(self):
        """事件应该支持置信度"""
        event = TranscriptEvent(
            text="Hello",
            confidence=0.95,
        )
        assert event.confidence == 0.95


class TestHallucinationFilter:
    """测试幻觉过滤"""

    def test_filter_short_text(self):
        """短文本应该被过滤"""
        config = ProcessorConfig(provider="Groq", model="test")
        mock_stt_service = MagicMock()

        processor = SimulatedStreamingProcessor(
            config=config,
            stt_service=mock_stt_service,
        )

        assert processor._is_valid_text("ab") is False
        assert processor._is_valid_text("abc") is False

    def test_filter_punctuation_only(self):
        """纯标点应该被过滤"""
        config = ProcessorConfig(provider="Groq", model="test")
        mock_stt_service = MagicMock()

        processor = SimulatedStreamingProcessor(
            config=config,
            stt_service=mock_stt_service,
        )

        assert processor._is_valid_text("...") is False
        assert processor._is_valid_text("？！") is False

    def test_filter_common_hallucinations(self):
        """常见幻觉应该被过滤"""
        config = ProcessorConfig(provider="Groq", model="test")
        mock_stt_service = MagicMock()

        processor = SimulatedStreamingProcessor(
            config=config,
            stt_service=mock_stt_service,
        )

        assert processor._is_valid_text("Thank you.") is False
        assert processor._is_valid_text("谢谢。") is False
        assert processor._is_valid_text("Okay.") is False

    def test_valid_text_passes(self):
        """正常文本应该通过"""
        config = ProcessorConfig(provider="Groq", model="test")
        mock_stt_service = MagicMock()

        processor = SimulatedStreamingProcessor(
            config=config,
            stt_service=mock_stt_service,
        )

        assert processor._is_valid_text("Hello, how are you?") is True
        assert processor._is_valid_text("This is a valid sentence.") is True
