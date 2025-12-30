"""
Sentence Builder
句子累积器 - 负责将 final 片段累积成完整句子并触发翻译

核心逻辑：
1. 累积每个 Deepgram final 的文本
2. 检测句末标点（. ! ? 。 ！ ？）
3. 遇到句末标点时，返回完整句子供翻译
4. 硬阈值切分时，未完成句子保留到下一个 segment
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class SentenceToTranslate:
    """待翻译的句子"""

    text: str
    segment_id: str
    sentence_index: int


class SentenceBuilder:
    """句子累积器

    将连续的 Deepgram final 片段累积成完整句子。
    当检测到句末标点时，返回完整句子供翻译。

    Attributes:
        buffer: 当前累积的文本（尚未形成完整句子）
        locked_segment_id: 当前句子锁定的 segment ID（在句子开始时锁定）
        current_segment_id: 最新的 segment ID（用于兼容）
        sentence_index: 当前 segment 内的句子索引（从 0 开始）
    """

    # 句末标点正则（支持中英文）
    SENTENCE_END_PATTERN = re.compile(r"[.!?。！？]\s*$")

    def __init__(self):
        self.buffer: str = ""
        self.locked_segment_id: str = ""  # 句子开始时锁定的 segment_id
        self.current_segment_id: str = ""  # 保留兼容
        self.sentence_index: int = 0

    def add_final(self, text: str, segment_id: str) -> list[SentenceToTranslate]:
        """累积 final 片段，返回需要翻译的句子列表

        Args:
            text: Deepgram final 的文本
            segment_id: 当前 segment 的 ID

        Returns:
            需要翻译的句子列表（可能为空，可能有多个）
        """
        if not text or not text.strip():
            return []

        # 更新 current_segment_id（保留兼容）
        self.current_segment_id = segment_id

        # ✅ 只在 buffer 为空（新句子开始）时锁定 segment_id
        # 这确保即使后续发生卡片切分，句子的翻译仍归属正确的卡片
        if not self.buffer:
            self.locked_segment_id = segment_id

        # 累积文本
        if self.buffer:
            self.buffer += " " + text.strip()
        else:
            self.buffer = text.strip()

        # 检查是否包含完整句子
        return self._extract_sentences()

    def _extract_sentences(self) -> list[SentenceToTranslate]:
        """从 buffer 中提取完整句子"""
        sentences: list[SentenceToTranslate] = []

        # 按句末标点分割
        # 注意：保留标点符号在句子末尾
        parts = re.split(r"([.!?。！？])\s*", self.buffer)

        # parts 格式: ['句子1', '.', '句子2', '!', '未完成部分']
        # 偶数索引是文本，奇数索引是标点

        complete_text = ""
        i = 0
        while i < len(parts) - 1:  # -1 因为最后一个可能是未完成的
            if i + 1 < len(parts):
                text = parts[i]
                punct = parts[i + 1] if i + 1 < len(parts) else ""

                if punct in ".!?。！？":
                    # 完整句子
                    sentence_text = (text + punct).strip()
                    if sentence_text:
                        sentences.append(
                            SentenceToTranslate(
                                text=sentence_text,
                                segment_id=self.locked_segment_id,  # 使用锁定的 ID
                                sentence_index=self.sentence_index,
                            )
                        )
                        self.sentence_index += 1
                    i += 2
                else:
                    # 不是标点，继续累积
                    complete_text += parts[i]
                    i += 1
            else:
                break

        # 剩余未完成的部分留在 buffer
        remaining_parts = parts[i:] if i < len(parts) else []
        self.buffer = "".join(remaining_parts).strip()

        return sentences

    def flush(self) -> list[SentenceToTranslate]:
        """强制返回剩余内容（停止录音时调用）

        Returns:
            剩余内容作为一个句子（如果有的话）
        """
        if not self.buffer.strip():
            return []

        sentence = SentenceToTranslate(
            text=self.buffer.strip(),
            segment_id=self.locked_segment_id,  # 使用锁定的 ID
            sentence_index=self.sentence_index,
        )
        self.buffer = ""
        self.sentence_index += 1
        return [sentence]

    def reset_for_new_segment(self, new_segment_id: str) -> list[SentenceToTranslate]:
        """新 segment 开始时调用，重置 sentence_index

        注意：强制 flush buffer，确保旧 segment 的剩余内容被翻译。
        这虽然会导致断句不完美，但能保证卡片内容的完整性和对齐。
        """
        # 1. 强制 Flush 旧内容
        flushed_sentences = self.flush()

        # 2. 更新状态
        self.current_segment_id = new_segment_id
        # self.locked_segment_id 会在下一个新句子开始时自动设置
        self.sentence_index = 0

        return flushed_sentences

    def get_incomplete_text(self) -> str:
        """获取未完成的文本（用于硬阈值切分时的处理）"""
        return self.buffer

    def clear_buffer(self):
        """清空 buffer（通常在软阈值切分后调用）"""
        self.buffer = ""

    def reset(self):
        """完全重置状态（新录音开始时调用）"""
        self.buffer = ""
        self.locked_segment_id = ""
        self.current_segment_id = ""
        self.sentence_index = 0
