"""
Ordered Translation Sender
顺序发送翻译结果

核心逻辑：
1. 翻译任务并行执行（保证效率）
2. 结果按 sentence_index 顺序发送（保证顺序）
3. 前面的翻译未到达时，后面的翻译缓存等待
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

from app.services.websocket.translation_handler import TranslationResult


class OrderedTranslationSender:
    """顺序发送翻译结果

    翻译任务并行执行，但结果按 sentence_index 顺序发送。
    确保前面的翻译未到达时，后面的翻译等待。

    使用方式:
    1. 创建实例时传入发送回调
    2. 翻译完成后调用 on_translation_complete()
    3. 卡片切分前调用 flush_all() 确保所有翻译都已发送
    4. 新 segment 开始时调用 reset()

    Attributes:
        send_callback: 发送翻译的回调函数
        results: 缓存的翻译结果 (index -> result)
        next_to_send: 下一个应该发送的 index
    """

    def __init__(self, send_callback: Callable[[TranslationResult], Awaitable[Any]]):
        """初始化

        Args:
            send_callback: 发送翻译的异步回调函数
        """
        self.send_callback = send_callback
        self.results: dict[int, TranslationResult] = {}
        self.next_to_send: int = 0
        self._lock = asyncio.Lock()

    async def on_translation_complete(self, result: TranslationResult):
        """翻译完成回调

        将翻译结果放入缓存，并尝试发送所有连续就绪的翻译。

        Args:
            result: 翻译结果（包含 sentence_index）
        """
        async with self._lock:
            self.results[result.sentence_index] = result
            await self._flush_ready()

    async def _flush_ready(self):
        """发送所有连续就绪的翻译

        从 next_to_send 开始，发送所有连续存在的翻译结果。
        """
        while self.next_to_send in self.results:
            result = self.results.pop(self.next_to_send)
            await self.send_callback(result)
            self.next_to_send += 1

    async def flush_all(self):
        """强制发送所有待发送的翻译（按顺序）

        用于卡片切分或停止录音时，确保所有翻译都已发送。
        如果有未到达的翻译（中间有空洞），按现有顺序发送已有的。
        """
        async with self._lock:
            # 按 index 顺序发送所有缓存的结果
            for idx in sorted(self.results.keys()):
                await self.send_callback(self.results[idx])
            self.results.clear()

    def reset(self):
        """重置状态（新 segment 开始时调用）"""
        self.results.clear()
        self.next_to_send = 0

    def has_pending(self) -> bool:
        """检查是否有待发送的翻译"""
        return len(self.results) > 0

    @property
    def pending_count(self) -> int:
        """获取待发送翻译数量"""
        return len(self.results)
