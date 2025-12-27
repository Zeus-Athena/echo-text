"""
Translation Handler
翻译策略处理器 - 支持极速模式和节流模式
"""

from __future__ import annotations

import asyncio

from loguru import logger

from app.services.llm_service import LLMService


class TranslationHandler:
    """翻译处理器，根据 buffer_duration 选择策略"""

    def __init__(
        self,
        llm_service: LLMService,
        buffer_duration: float,
        source_lang: str = "en",
        target_lang: str = "zh",
        translation_timeout: float = 10.0,
    ):
        self.llm_service = llm_service
        self.buffer_duration = buffer_duration
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.translation_timeout = translation_timeout

        # 状态
        self._buffer: str = ""
        self._last_word_count: int = 0
        self._last_context: str = ""

    def reset(self):
        """重置状态"""
        self._buffer = ""
        self._last_word_count = 0

    async def handle_transcript(
        self,
        text: str,
        is_final: bool,
    ) -> dict | None:
        """
        处理转录结果，根据策略决定是否翻译

        返回:
            {"text": "翻译结果", "is_final": bool} 或 None（不需要翻译）
        """
        if self.buffer_duration == 0:
            return await self._fast_mode(text, is_final)
        else:
            return await self._throttle_mode(text, is_final)

    async def flush(self) -> dict | None:
        """
        强制翻译剩余缓冲区（用于停止录制时）
        """
        if self._buffer.strip():
            result = await self._translate(self._buffer, is_final=True)
            self._buffer = ""
            return result
        return None

    async def _fast_mode(self, text: str, is_final: bool) -> dict | None:
        """
        极速模式：翻译 interim + final
        - final 无条件翻译
        - interim 每增加 5 词翻译一次
        """
        if is_final:
            self._last_word_count = 0
            return await self._translate(text, is_final=True)

        # interim: 检查词数增量
        current = len(text.split())
        if current >= self._last_word_count + 5:
            self._last_word_count = current
            return await self._translate(text, is_final=False)

        return None

    async def _throttle_mode(self, text: str, is_final: bool) -> dict | None:
        """
        节流模式：只翻译 final，累积到句末标点/50词再发送
        """
        if not is_final:
            return None

        self._buffer += (" " if self._buffer else "") + text

        if self._should_flush():
            result = await self._translate(self._buffer, is_final=True)
            self._buffer = ""
            return result

        return None

    def _should_flush(self) -> bool:
        """检查是否应该翻译缓冲区"""
        text = self._buffer.strip()
        if not text:
            return False

        # 句末标点
        if text[-1] in ".!?。！？":
            return True

        # 50 词上限
        return len(text.split()) >= 50

    async def _translate(self, text: str, is_final: bool) -> dict | None:
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

            return {"text": translated, "is_final": is_final}

        except TimeoutError:
            logger.warning(f"Translation timeout for: {text[:50]}...")
            return None
        except Exception as e:
            logger.warning(f"Translation error: {e}")
            return None
