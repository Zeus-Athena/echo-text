"""
Translation Handler V2
翻译处理器 - 重构版（按完整句子翻译）

核心变化：
1. 接收 SentenceBuilder 输出的完整句子
2. 翻译结果带 segment_id + sentence_index 保证顺序
3. RPM 控制升级为令牌桶算法 (Token Bucket)，支持突发
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from loguru import logger

from app.services.llm_service import LLMService
from app.services.websocket.sentence_builder import SentenceToTranslate


@dataclass
class TranslationResult:
    """翻译结果"""

    text: str
    segment_id: str
    sentence_index: int
    is_final: bool = True
    error: bool = False


class TranslationHandler:
    """翻译处理器

    接收 SentenceBuilder 输出的完整句子，执行翻译，
    返回带 segment_id + sentence_index 的结果以保证前端显示顺序。

    Attributes:
        llm_service: LLM 服务实例
        rpm_limit: 每分钟最大请求数
        capacity: 令牌桶容量（最大突发数）
    """

    # 默认 RPM 限制
    DEFAULT_RPM_LIMIT = 100
    # 默认桶容量（突发限制）
    DEFAULT_CAPACITY = 10

    def __init__(
        self,
        llm_service: LLMService,
        source_lang: str = "en",
        target_lang: str = "zh",
        translation_timeout: float = 15.0,
        rpm_limit: int = DEFAULT_RPM_LIMIT,
        # 保留 buffer_duration 参数以兼容现有调用
        buffer_duration: float = 0.0,
    ):
        self.llm_service = llm_service
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.translation_timeout = translation_timeout

        # 保留兼容参数（未来可移除）
        self.buffer_duration = buffer_duration

        # RPM 控制（令牌桶算法）
        self.rpm_limit = rpm_limit
        self.capacity = self.DEFAULT_CAPACITY
        # 计算回血速率 (tokens/sec)
        self.refill_rate = rpm_limit / 60.0

        # 初始状态：桶满
        self.tokens = float(self.capacity)
        self.last_update = time.monotonic()

        # 上下文（用于翻译连贯性）
        self._last_context: str = ""

    def reset(self):
        """重置状态（新录音开始时调用）"""
        # 重置时桶也回满
        self.tokens = float(self.capacity)
        self.last_update = time.monotonic()
        self._last_context = ""

    async def translate_sentence(
        self,
        sentence: SentenceToTranslate,
        on_complete: Callable[[TranslationResult], Awaitable[None]] | None = None,
    ) -> TranslationResult:
        """翻译单个句子

        这是新的核心方法，替代旧的 handle_transcript。

        Args:
            sentence: 待翻译的句子（来自 SentenceBuilder）
            on_complete: 翻译完成后的异步回调（无论成功失败都会调用）

        Returns:
            翻译结果（带 segment_id 和 sentence_index）
        """
        result: TranslationResult

        if not sentence.text.strip():
            result = TranslationResult(
                text="",
                segment_id=sentence.segment_id,
                sentence_index=sentence.sentence_index,
                is_final=True,
                error=True,
            )
            if on_complete:
                await on_complete(result)
            return result

        # 等待令牌（Token Bucket）
        await self._wait_for_rate_limit()

        try:
            translated = await asyncio.wait_for(
                self.llm_service.translate(
                    sentence.text,
                    source_lang=self.source_lang,
                    target_lang=self.target_lang,
                    context=self._last_context,
                ),
                timeout=self.translation_timeout,
            )

            # 更新上下文
            self._last_context = sentence.text

            result = TranslationResult(
                text=translated,
                segment_id=sentence.segment_id,
                sentence_index=sentence.sentence_index,
                is_final=True,
            )

        except TimeoutError:
            logger.warning(f"Translation timeout for: {sentence.text[:50]}...")
            result = TranslationResult(
                text="[翻译超时]",
                segment_id=sentence.segment_id,
                sentence_index=sentence.sentence_index,
                is_final=True,
                error=True,
            )
        except Exception as e:
            logger.warning(f"Translation error: {e}")
            result = TranslationResult(
                text="[翻译失败]",
                segment_id=sentence.segment_id,
                sentence_index=sentence.sentence_index,
                is_final=True,
                error=True,
            )

        # 触发回调
        if on_complete:
            try:
                await on_complete(result)
            except Exception as e:
                logger.error(f"Error in translation completion callback: {e}")

        return result

    async def _wait_for_rate_limit(self):
        """等待 RPM 限速（令牌桶算法）"""
        while True:
            now = time.monotonic()
            elapsed = now - self.last_update

            # 1. 回血 (Refill)
            # 计算这段时间产生的新令牌
            new_tokens = elapsed * self.refill_rate

            if new_tokens > 0:
                self.tokens = min(self.capacity, self.tokens + new_tokens)
                self.last_update = now

            # 2. 扣费 (Consume)
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return  # 立即放行

            # 3. 等待 (Wait)
            # 计算攒够 1 个令牌还需要多久
            needed = 1.0 - self.tokens
            wait_time = needed / self.refill_rate

            # 加上一点点buffer防止浮点数误差
            wait_time = max(0.01, wait_time)

            # logger.debug(f"Throttling: tokens={self.tokens:.2f}, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            # 醒来后循环继续，重新计算回血和扣费

    # ===== 兼容旧 API（过渡期使用，后续可删除）=====

    async def handle_transcript(
        self,
        text: str,
        is_final: bool,
        transcript_id: str = "",
    ) -> list[dict]:
        """
        【兼容方法】处理转录结果

        为保持向后兼容而保留，新代码应使用 translate_sentence。

        返回:
            list[dict]: 翻译结果列表 [{"text": "...", "is_final": bool, "transcript_id": str}, ...]
        """
        if not is_final:
            return []

        if not text.strip():
            return []

        # 等待 RPM 限速
        await self._wait_for_rate_limit()

        try:
            translated = await asyncio.wait_for(
                self.llm_service.translate(
                    text,
                    source_lang=self.source_lang,
                    target_lang=self.target_lang,
                    context=self._last_context,
                ),
                timeout=self.translation_timeout,
            )

            self._last_context = text

            return [{"text": translated, "is_final": is_final, "transcript_id": transcript_id}]

        except TimeoutError:
            logger.warning(f"Translation timeout for: {text[:50]}...")
            return []
        except Exception as e:
            logger.warning(f"Translation error: {e}")
            return []

    async def flush(self, transcript_id: str = "") -> list[dict]:
        """
        【兼容方法】强制翻译

        新逻辑下不再有积压的 buffer，直接返回空。
        """
        return []
