"""
Segment Builder
卡片切分器 - 负责将多个 final 片段切分成卡片（Segment）

核心逻辑：
1. 累积每个 Deepgram final 的文本和时间戳
2. 软阈值（如 30 词）+ 句末标点 → 触发切分
3. 硬阈值（如 60 词）→ 强制切分
4. 切分时生成新的 segment_id
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field


@dataclass
class SegmentData:
    """切分后的卡片数据"""

    segment_id: str
    text: str
    start: float
    end: float
    word_count: int


class SegmentBuilder:
    """卡片切分器

    将连续的 Deepgram final 片段按阈值切分成卡片。

    Attributes:
        soft_threshold: 软阈值（词数），超过后遇到句末标点触发切分
        hard_threshold: 硬阈值（词数），超过后强制切分
        buffer: 当前累积的文本
        start_time: 当前 segment 的开始时间
        end_time: 当前 segment 的结束时间
        current_segment_id: 当前 segment 的 ID
    """

    # 句末标点正则（支持中英文）
    SENTENCE_END_PATTERN = re.compile(r"[.!?。！？]\s*$")

    def __init__(
        self,
        soft_threshold: int = 30,
        hard_threshold: int = 60,
    ):
        if soft_threshold >= hard_threshold:
            raise ValueError("soft_threshold must be less than hard_threshold")

        self.soft_threshold = soft_threshold
        self.hard_threshold = hard_threshold

        # 初始化状态
        self.buffer: str = ""
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self._has_start_time: bool = False  # 标志位：是否已设置开始时间
        self._current_segment_id: str = self._generate_segment_id()

    @staticmethod
    def _generate_segment_id() -> str:
        """生成唯一的 segment ID"""
        return str(uuid.uuid4())

    @property
    def current_segment_id(self) -> str:
        """获取当前 segment ID"""
        return self._current_segment_id

    @property
    def word_count(self) -> int:
        """获取当前文本的词数"""
        if not self.buffer.strip():
            return 0
        return len(self.buffer.split())

    def add_final(self, text: str, start_time: float, end_time: float) -> str:
        """累积 final 片段

        Args:
            text: Deepgram final 的文本
            start_time: 片段开始时间（秒）
            end_time: 片段结束时间（秒）

        Returns:
            当前 segment 的 ID
        """
        if not text or not text.strip():
            return self._current_segment_id

        # 累积文本
        if self.buffer:
            self.buffer += " " + text.strip()
        else:
            self.buffer = text.strip()

        # 更新时间戳
        if not self._has_start_time:
            self.start_time = start_time
            self._has_start_time = True
        self.end_time = end_time

        return self._current_segment_id

    def check_split(self) -> SegmentData | None:
        """检查是否需要切分

        Returns:
            如果需要切分，返回切分的 segment 数据；否则返回 None
        """
        if not self.buffer.strip():
            return None

        word_count = self.word_count
        ends_with_punctuation = bool(self.SENTENCE_END_PATTERN.search(self.buffer))

        should_split = False

        # 软阈值 + 句末标点
        if word_count >= self.soft_threshold and ends_with_punctuation:
            should_split = True

        # 硬阈值（强制切分）
        if word_count >= self.hard_threshold:
            should_split = True

        if should_split:
            return self._do_split()

        return None

    def _do_split(self) -> SegmentData:
        """执行切分操作"""
        segment = SegmentData(
            segment_id=self._current_segment_id,
            text=self.buffer,
            start=self.start_time,
            end=self.end_time,
            word_count=self.word_count,
        )

        # 重置状态
        self.buffer = ""
        self.start_time = 0.0
        self.end_time = 0.0
        self._has_start_time = False
        self._current_segment_id = self._generate_segment_id()

        return segment

    def force_split(self) -> SegmentData | None:
        """强制切分（停止录音时调用）

        Returns:
            当前 segment 数据（如果有内容）
        """
        if not self.buffer.strip():
            return None
        return self._do_split()

    def get_current_state(self) -> dict:
        """获取当前状态（用于调试）"""
        return {
            "segment_id": self._current_segment_id,
            "buffer": self.buffer,
            "word_count": self.word_count,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }

    def reset(self):
        """完全重置状态（新录音开始时调用）"""
        self.buffer = ""
        self.start_time = 0.0
        self.end_time = 0.0
        self._has_start_time = False
        self._current_segment_id = self._generate_segment_id()
