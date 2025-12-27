"""
Tests for Audio Processors
测试音频处理器模块
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.audio_processors.base import (
    ProcessorConfig,
    TranscriptEvent,
)
from app.services.audio_processors.factory import ProcessorFactory
from app.services.audio_processors.simulated import SimulatedStreamingProcessor
from app.services.audio_processors.true_streaming import TrueStreamingProcessor


class TestProcessorConfig:
    """测试处理器配置"""

    def test_config_creation(self):
        """应该能创建配置"""
        config = ProcessorConfig(
            provider="Groq",
            model="whisper-large-v3-turbo",
            source_lang="en",
            target_lang="zh",
        )
        assert config.provider == "Groq"
        assert config.model == "whisper-large-v3-turbo"
        assert config.source_lang == "en"
        assert config.target_lang == "zh"

    def test_config_defaults(self):
        """配置应该有默认值"""
        config = ProcessorConfig(
            provider="Groq",
            model="test",
        )
        assert config.silence_threshold == 30.0
        assert config.buffer_duration == 6.0
        assert config.diarization is False


class TestTranscriptEvent:
    """测试转录事件"""

    def test_event_creation(self):
        """应该能创建事件"""
        event = TranscriptEvent(
            text="Hello world",
            is_final=True,
            speaker="Speaker 1",
        )
        assert event.text == "Hello world"
        assert event.is_final is True
        assert event.speaker == "Speaker 1"

    def test_event_defaults(self):
        """事件应该有默认值"""
        event = TranscriptEvent(text="Test")
        assert event.is_final is False
        assert event.speaker is None
        assert event.start_time == 0.0
        assert event.confidence == 1.0


class TestProcessorFactory:
    """测试处理器工厂"""

    def test_create_simulated_processor_for_groq(self):
        """Groq 应该创建 SimulatedStreamingProcessor"""
        config = ProcessorConfig(provider="Groq", model="whisper-large-v3-turbo")
        mock_stt_service = MagicMock()

        processor = ProcessorFactory.create(
            config=config,
            stt_service=mock_stt_service,
        )

        assert isinstance(processor, SimulatedStreamingProcessor)

    def test_create_true_streaming_processor_for_deepgram(self):
        """Deepgram 应该创建 TrueStreamingProcessor"""
        config = ProcessorConfig(provider="Deepgram", model="nova-3")

        processor = ProcessorFactory.create(config=config)

        assert isinstance(processor, TrueStreamingProcessor)

    def test_unknown_provider_falls_back_to_simulated(self):
        """未知供应商应该回退到 SimulatedStreamingProcessor"""
        config = ProcessorConfig(provider="UnknownProvider", model="test")
        mock_stt_service = MagicMock()

        processor = ProcessorFactory.create(
            config=config,
            stt_service=mock_stt_service,
        )

        assert isinstance(processor, SimulatedStreamingProcessor)

    def test_simulated_requires_stt_service(self):
        """SimulatedStreamingProcessor 需要 stt_service"""
        config = ProcessorConfig(provider="Groq", model="test")

        with pytest.raises(ValueError, match="STTService is required"):
            ProcessorFactory.create(config=config)

    def test_get_supported_features_groq(self):
        """应该返回 Groq 的特性"""
        features = ProcessorFactory.get_supported_features("Groq")
        assert "vad_threshold" in features
        assert "buffer_duration" in features

    def test_get_supported_features_deepgram(self):
        """应该返回 Deepgram 的特性"""
        features = ProcessorFactory.get_supported_features("Deepgram")
        assert "diarization" in features
        assert "interim_results" in features

    def test_is_streaming_groq(self):
        """Groq 不应该是流式"""
        assert ProcessorFactory.is_streaming("Groq") is False

    def test_is_streaming_deepgram(self):
        """Deepgram 应该是流式"""
        assert ProcessorFactory.is_streaming("Deepgram") is True


class TestSimulatedStreamingProcessor:
    """测试伪流式处理器"""

    @pytest.fixture
    def config(self):
        return ProcessorConfig(
            provider="Groq",
            model="whisper-large-v3-turbo",
            source_lang="en",
            target_lang="zh",
            silence_threshold=30.0,
            buffer_duration=3.0,
        )

    @pytest.fixture
    def mock_stt_service(self):
        service = MagicMock()
        service.transcribe = AsyncMock(return_value={"text": "test transcription"})
        return service

    def test_processor_initialization(self, config, mock_stt_service):
        """应该能初始化处理器"""
        processor = SimulatedStreamingProcessor(
            config=config,
            stt_service=mock_stt_service,
        )
        assert processor.config == config
        assert processor.stt_service == mock_stt_service

    @pytest.mark.asyncio
    async def test_start_resets_state(self, config, mock_stt_service):
        """start() 应该重置状态"""
        processor = SimulatedStreamingProcessor(
            config=config,
            stt_service=mock_stt_service,
        )

        await processor.start()

        assert processor.is_active is True
        assert processor.chunk_count == 0

    @pytest.mark.asyncio
    async def test_process_audio_saves_chunk(self, config, mock_stt_service):
        """process_audio() 应该保存音频块"""
        processor = SimulatedStreamingProcessor(
            config=config,
            stt_service=mock_stt_service,
        )

        await processor.start()
        await processor.process_audio(b"test_audio_chunk")

        assert processor.chunk_count == 1

    @pytest.mark.asyncio
    async def test_stop_returns_audio_data(self, config, mock_stt_service):
        """stop() 应该返回完整的音频数据"""
        processor = SimulatedStreamingProcessor(
            config=config,
            stt_service=mock_stt_service,
        )

        await processor.start()
        await processor.process_audio(b"chunk1")
        await processor.process_audio(b"chunk2")

        header, data = await processor.stop()

        assert processor.is_active is False
        assert b"chunk1" in data
        assert b"chunk2" in data


class TestTrueStreamingProcessor:
    """测试真流式处理器"""

    @pytest.fixture
    def config(self):
        return ProcessorConfig(
            provider="Deepgram",
            model="nova-3",
            source_lang="en",
            target_lang="zh",
            api_key="test_key",
            diarization=True,
        )

    def test_processor_initialization(self, config):
        """应该能初始化处理器"""
        processor = TrueStreamingProcessor(config=config)
        assert processor.config == config

    @pytest.mark.asyncio
    async def test_process_audio_saves_chunk_locally(self, config):
        """即使是真流式，也应该保存音频块到本地"""
        processor = TrueStreamingProcessor(config=config)

        # Mock the upstream connection (we don't want to actually connect)
        processor._upstream_ws = None
        processor._is_active = True

        # Call the base class's save method directly
        processor._save_chunk(b"test_chunk")

        assert processor.chunk_count == 1
