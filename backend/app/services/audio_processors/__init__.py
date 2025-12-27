"""
Audio Processors Module
音频处理器模块 - 策略模式实现
"""

from .base import BaseAudioProcessor, ProcessorConfig, TranscriptEvent
from .factory import ProcessorFactory
from .simulated import SimulatedStreamingProcessor
from .true_streaming import TrueStreamingProcessor

__all__ = [
    "BaseAudioProcessor",
    "TranscriptEvent",
    "ProcessorConfig",
    "SimulatedStreamingProcessor",
    "TrueStreamingProcessor",
    "ProcessorFactory",
]
