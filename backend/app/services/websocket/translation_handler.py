"""
Translation Handler
翻译策略处理器 - 支持极速模式和节流模式（基于时间间隔的 RPM 控制）
"""

from __future__ import annotations

import asyncio
import time

from loguru import logger

from app.services.llm_service import LLMService


class TranslationHandler:
    """翻译处理器，根据 buffer_duration 选择策略

    极速模式 (buffer_duration=0):
        每个 is_final 立即翻译，适用于伪流式（Groq/OpenAI）

    节流模式 (buffer_duration>0):
        使用时间间隔控制发送频率，保证 RPM 不超限
        每个 transcript_id 单独翻译，彻底解决错位问题
    """

    # 默认 RPM 限制（每分钟最大请求次数）
    DEFAULT_RPM_LIMIT = 20

    def __init__(
        self,
        llm_service: LLMService,
        buffer_duration: float,
        source_lang: str = "en",
        target_lang: str = "zh",
        translation_timeout: float = 15.0,
        rpm_limit: int = DEFAULT_RPM_LIMIT,
    ):
        self.llm_service = llm_service
        self.buffer_duration = buffer_duration
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.translation_timeout = translation_timeout

        # RPM 控制
        self.rpm_limit = rpm_limit
        self.min_interval = 60.0 / rpm_limit  # 最小间隔（秒）
        self._last_request_time: float = 0.0

        # 上下文（用于翻译连贯性）
        self._last_context: str = ""

    def reset(self):
        """重置状态"""
        self._last_request_time = 0.0
        self._last_context = ""

    async def handle_transcript(
        self,
        text: str,
        is_final: bool,
        transcript_id: str = "",
    ) -> list[dict]:
        """
        处理转录结果，根据策略决定是否翻译

        返回:
            list[dict]: 翻译结果列表 [{"text": "...", "is_final": bool, "transcript_id": str}, ...]
        """
        if self.buffer_duration == 0:
            return await self._fast_mode(text, is_final, transcript_id)
        else:
            return await self._throttle_mode(text, is_final, transcript_id)

    async def flush(self, transcript_id: str = "") -> list[dict]:
        """
        强制翻译（用于停止录制时）
        节流模式下每个 ID 已单独处理，无需额外 flush
        """
        # 新逻辑下不再有积压的 buffer，直接返回空
        return []

    async def _fast_mode(self, text: str, is_final: bool, transcript_id: str = "") -> list[dict]:
        """
        极速模式：只翻译 Final（不翻译 interim）
        一个 final 对应一次翻译调用，适用于伪流式
        """
        if not is_final:
            return []

        res = await self._translate(text, is_final=True, transcript_id=transcript_id)
        return [res] if res else []

    async def _throttle_mode(
        self, text: str, is_final: bool, transcript_id: str = ""
    ) -> list[dict]:
        """
        节流模式（基于时间间隔控制 RPM）：
        - 每个 is_final 单独翻译（解决错位问题）
        - 通过等待时间间隔来控制 RPM 不超限
        """
        if not is_final:
            return []

        # 计算需要等待的时间
        now = time.time()
        elapsed = now - self._last_request_time
        wait_time = self.min_interval - elapsed

        if wait_time > 0:
            logger.debug(f"Throttling: waiting {wait_time:.2f}s before translation")
            await asyncio.sleep(wait_time)

        # 更新最后请求时间
        self._last_request_time = time.time()

        # 单独翻译这个 transcript_id
        res = await self._translate(text, is_final=True, transcript_id=transcript_id)
        return [res] if res else []

    async def _translate(self, text: str, is_final: bool, transcript_id: str = "") -> dict | None:
        """执行翻译"""
        if not text.strip():
            return None

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

            if is_final:
                self._last_context = text

            return {"text": translated, "is_final": is_final, "transcript_id": transcript_id}

        except TimeoutError:
            logger.warning(f"Translation timeout for: {text[:50]}...")
            return None
        except Exception as e:
            logger.warning(f"Translation error: {e}")
            return None
