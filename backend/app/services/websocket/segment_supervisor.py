"""
Segment Supervisor
卡片生命周期管理器 - 取代原 SegmentBuilder，负责原子性切分与状态管理

职责：
1. 接收转录片段，维护当前 Segment 的状态（文本、时间戳、词数）
2. 根据软硬阈值策略决定切分时机
3. 生成 Segment 生命周期事件（Created, Updated, Closed）
4. 确保 Segment ID 的权威性
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field


@dataclass
class SegmentEvent:
    """Segment 生命周期事件"""

    type: str  # 'created', 'updated', 'closed'
    segment_id: str
    data: dict = field(default_factory=dict)


class SegmentSupervisor:
    """卡片生命周期监工"""

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

        # 当前状态
        self.buffer: str = ""
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self._has_start_time: bool = False
        self._current_segment_id: str = self._generate_segment_id()

        # 记录已发出的事件，用于去重或状态追踪（可选）
        self.events_history: list[SegmentEvent] = []

    @staticmethod
    def _generate_segment_id() -> str:
        return str(uuid.uuid4())

    @property
    def current_segment_id(self) -> str:
        return self._current_segment_id

    @property
    def word_count(self) -> int:
        if not self.buffer.strip():
            return 0
        return len(self.buffer.strip().split())

    def add_transcript(self, text: str, start: float, end: float) -> list[SegmentEvent]:
        """处理新的转录片段，并返回产生的事件列表"""
        events = []

        if not text or not text.strip():
            # 即使没有文本更新，时间戳可能也需要更新？通常 Deepgram final 总有文本
            return events

        # 1. 如果是新 Segment 的第一个片段，可能需要发 Created 事件（视前端需求而定）
        # 在我们的架构中，通常 update 隐含了 create，或者第一次 update 就是 create
        # 但为了严谨，我们可以标记状态

        # 累积文本
        if self.buffer:
            self.buffer += " " + text.strip()
        else:
            self.buffer = text.strip()
            # 首次有内容，标记开始时间
            if not self._has_start_time:
                self.start_time = start
                self._has_start_time = True
                # 发出 Created 事件（可选，或者由第一次 Updated 携带）
                # events.append(SegmentEvent('created', self._current_segment_id))

        # 更新结束时间
        self.end_time = end

        # 2. 发出 Updated 事件（通知前端当前 Segment 内容变化）
        events.append(
            SegmentEvent(
                type="updated",
                segment_id=self._current_segment_id,
                data={
                    "text": self.buffer,
                    "start": self.start_time,
                    "end": self.end_time,
                    "is_final": False,  # 尚未 Close
                },
            )
        )

        # 3. 检查是否需要切分
        start_new, closed_segment_data = self._check_split_criteria()

        if start_new and closed_segment_data:
            # 发出 Closed 事件
            events.append(
                SegmentEvent(
                    type="closed",
                    segment_id=closed_segment_data["segment_id"],
                    data=closed_segment_data,
                )
            )

            # 准备新 Segment
            self._reset_for_new_segment()

            # 发出新 Segment 的 Created 事件
            events.append(
                SegmentEvent(
                    type="created",
                    segment_id=self._current_segment_id,
                    data={"start": 0.0},  # 初始为空
                )
            )

        return events

    def _check_split_criteria(self) -> tuple[bool, dict | None]:
        """检查切分标准，返回 (是否切分, 切分的Segment数据)"""
        if not self.buffer.strip():
            return False, None

        word_count = self.word_count
        ends_with_punctuation = bool(self.SENTENCE_END_PATTERN.search(self.buffer))

        should_split = False

        if word_count >= self.soft_threshold and ends_with_punctuation:
            should_split = True
        elif word_count >= self.hard_threshold:
            should_split = True

        if should_split:
            # 准备 Closed 数据
            closed_data = {
                "segment_id": self._current_segment_id,
                "text": self.buffer,
                "start": self.start_time,
                "end": self.end_time,
                "word_count": word_count,
            }
            return True, closed_data

        return False, None

    def _reset_for_new_segment(self):
        """重置状态以开始新 Segment"""
        self.buffer = ""
        self.start_time = 0.0
        self.end_time = 0.0
        self._has_start_time = False
        self._current_segment_id = self._generate_segment_id()

    def force_close(self) -> list[SegmentEvent]:
        """强制关闭当前 Segment（如停止录音时）"""
        events = []
        if self.buffer.strip():
            closed_data = {
                "segment_id": self._current_segment_id,
                "text": self.buffer,
                "start": self.start_time,
                "end": self.end_time,
                "word_count": self.word_count,
            }
            events.append(
                SegmentEvent(type="closed", segment_id=self._current_segment_id, data=closed_data)
            )
            self._reset_for_new_segment()
        return events
