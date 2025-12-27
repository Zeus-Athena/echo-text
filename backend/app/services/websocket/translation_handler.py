"""
Translation Handler
翻译策略处理器 - 支持极速模式和节流模式
"""

from __future__ import annotations

import asyncio
import re

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
        translation_timeout: float = 30.0,
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
    ) -> list[dict]:
        """
        处理转录结果，根据策略决定是否翻译

        返回:
            list[dict]: 翻译结果列表 [{"text": "...", "is_final": bool}, ...]
        """
        if self.buffer_duration == 0:
            return await self._fast_mode(text, is_final)
        else:
            return await self._throttle_mode(text, is_final)

    async def flush(self) -> list[dict]:
        """
        强制翻译剩余缓冲区（用于停止录制时）
        """
        if self._buffer.strip():
            # 同样应用拆分逻辑
            results = await self._translate_sequentially(self._buffer, is_final=True)
            self._buffer = ""
            return results
        return []

    def _split_text(self, text: str) -> list[str]:
        """根据标点符号拆分文本，保留标点"""
        # 匹配中英文句末标点
        parts = re.split(r"([.!?。！？]+)", text)
        sentences = []

        # 重新组合句子和标点: "Hello" + "." -> "Hello."
        # parts list like: ['Hello', '.', 'World', '!', '']
        for i in range(0, len(parts) - 1, 2):
            sentence = parts[i] + parts[i + 1]
            if sentence.strip():
                sentences.append(sentence.strip())

        # 处理可能的剩余部分 (无标点结尾)
        if len(parts) % 2 != 0:
            tail = parts[-1]
            if tail.strip():
                sentences.append(tail.strip())

        return sentences

    async def _translate_sequentially(self, text: str, is_final: bool) -> list[dict]:
        """拆分文本并串行翻译"""
        sentences = self._split_text(text)
        results = []

        for sentence in sentences:
            if not sentence.strip():
                continue

            # 串行等待翻译完成
            res = await self._translate(sentence, is_final=is_final)
            if res:
                results.append(res)

        return results

    async def _fast_mode(self, text: str, is_final: bool) -> list[dict]:
        """
        极速模式：翻译 interim + final
        """
        if is_final:
            self._last_word_count = 0
            # 使用串行切分逻辑处理 Final
            return await self._translate_sequentially(text, is_final=True)

        # interim: 检查词数增量
        current = len(text.split())
        if current >= self._last_word_count + 5:
            self._last_word_count = current
            # Interim 不拆分，直接发 (保持快速)
            res = await self._translate(text, is_final=False)
            return [res] if res else []

        return []

    async def _throttle_mode(self, text: str, is_final: bool) -> list[dict]:
        """
        节流模式：只翻译 final，累积到句末标点/30词再发送
        """
        if not is_final:
            return []

        self._buffer += (" " if self._buffer else "") + text

        if self._should_flush():
            # 使用串行拆分逻辑
            results = await self._translate_sequentially(self._buffer, is_final=True)
            self._buffer = ""
            return results

        return []

    def _should_flush(self) -> bool:
        """检查是否应该翻译缓冲区"""
        text = self._buffer.strip()
        if not text:
            return False

        # 句末标点
        if text[-1] in ".!?。！？":
            return True

        # 30 词上限
        return len(text.split()) >= 30

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
