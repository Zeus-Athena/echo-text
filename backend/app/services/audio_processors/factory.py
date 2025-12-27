"""
Processor Factory
处理器工厂 - 根据供应商配置自动实例化正确的策略
"""

from collections.abc import Awaitable, Callable

from loguru import logger

from app.core.stt_registry import (
    STTProtocol,
    get_provider_config,
    get_provider_protocol,
    is_streaming_provider,
)
from app.services.stt_service import STTService

from .base import BaseAudioProcessor, ProcessorConfig, TranscriptEvent
from .simulated import SimulatedStreamingProcessor
from .true_streaming import TrueStreamingProcessor


class ProcessorFactory:
    """
    处理器工厂

    根据 STT_REGISTRY 中定义的协议类型，自动选择正确的策略。
    """

    @staticmethod
    def create(
        config: ProcessorConfig,
        stt_service: STTService | None = None,
        on_transcript: Callable[[TranscriptEvent], Awaitable[None]] | None = None,
        on_error: Callable[[str], Awaitable[None]] | None = None,
    ) -> BaseAudioProcessor:
        """
        创建处理器实例

        Args:
            config: 处理器配置
            stt_service: STT 服务实例 (仅 Simulated 需要)
            on_transcript: 转录结果回调
            on_error: 错误回调

        Returns:
            BaseAudioProcessor: 具体的处理器实例
        """
        provider = config.provider
        protocol = get_provider_protocol(provider)

        if protocol is None:
            # 未知供应商，默认使用 Simulated
            logger.warning(
                f"Unknown provider '{provider}', falling back to SimulatedStreamingProcessor"
            )
            protocol = STTProtocol.HTTP_BATCH

        logger.info(f"Creating processor for {provider}: protocol={protocol.value}")

        if protocol == STTProtocol.WEBSOCKET_STREAM:
            # 真流式
            return TrueStreamingProcessor(
                config=config,
                on_transcript=on_transcript,
                on_error=on_error,
            )
        else:
            # 伪流式 (默认)
            if stt_service is None:
                raise ValueError("STTService is required for SimulatedStreamingProcessor")

            return SimulatedStreamingProcessor(
                config=config,
                stt_service=stt_service,
                on_transcript=on_transcript,
                on_error=on_error,
            )

    @staticmethod
    def get_supported_features(provider: str) -> list[str]:
        """获取供应商支持的 UI 特性"""
        config = get_provider_config(provider)
        return config["ui_features"] if config else []

    @staticmethod
    def is_streaming(provider: str) -> bool:
        """判断供应商是否支持真流式"""
        return is_streaming_provider(provider)
