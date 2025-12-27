"""
WebSocket Session State
会话状态封装
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TranscriptionSession:
    """封装 WebSocket 转录会话状态"""

    client_id: str
    user_id: str
    recording_id: str | None = None
    source_lang: str = "en"
    target_lang: str = "zh"
    is_recording: bool = False
    audio_saved: bool = False

    # 翻译相关状态
    translation_buffer: str = ""
    last_interim_word_count: int = 0

    # 配置参数
    buffer_duration: float = 6.0
    silence_threshold: float = 30.0

    def reset_translation_state(self):
        """重置翻译状态"""
        self.translation_buffer = ""
        self.last_interim_word_count = 0

    def start_recording(
        self,
        recording_id: str | None = None,
        source_lang: str = "en",
        target_lang: str = "zh",
        silence_threshold: float | None = None,
    ):
        """开始录制"""
        self.is_recording = True
        self.audio_saved = False
        self.recording_id = recording_id
        self.source_lang = source_lang
        self.target_lang = target_lang
        if silence_threshold is not None:
            self.silence_threshold = silence_threshold
        self.reset_translation_state()

    def stop_recording(self):
        """停止录制"""
        self.is_recording = False

    def mark_audio_saved(self):
        """标记音频已保存"""
        self.audio_saved = True
