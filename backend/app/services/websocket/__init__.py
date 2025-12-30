# WebSocket Services Package
"""
WebSocket 服务模块 - 职责分离重构

包含:
- session.py: 会话状态封装
- connection_manager.py: 连接管理
- translation_handler.py: 翻译策略处理
- audio_saver.py: 音频保存处理
- sentence_builder.py: 句子累积器
- segment_builder.py: 卡片切分器
- ordered_translation_sender.py: 顺序发送翻译（新）
"""

from app.services.websocket.audio_saver import AudioSaver
from app.services.websocket.connection_manager import ConnectionManager
from app.services.websocket.ordered_translation_sender import OrderedTranslationSender
from app.services.websocket.segment_builder import SegmentBuilder, SegmentData
from app.services.websocket.sentence_builder import SentenceBuilder, SentenceToTranslate
from app.services.websocket.session import TranscriptionSession
from app.services.websocket.translation_handler import (
    TranslationHandler,
    TranslationResult,
)

__all__ = [
    "TranscriptionSession",
    "ConnectionManager",
    "TranslationHandler",
    "TranslationResult",
    "AudioSaver",
    "SentenceBuilder",
    "SentenceToTranslate",
    "SegmentBuilder",
    "SegmentData",
    "OrderedTranslationSender",
]

