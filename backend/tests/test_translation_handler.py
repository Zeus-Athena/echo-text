"""
Tests for websocket/translation_handler.py
翻译处理器单元测试
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestTranslationHandler:
    """TranslationHandler 单元测试"""

    @pytest.fixture
    def mock_llm_service(self):
        """创建 mock LLM 服务"""
        service = MagicMock()
        service.translate = AsyncMock(return_value="翻译结果")
        return service

    @pytest.fixture
    def handler_fast_mode(self, mock_llm_service):
        """极速模式处理器 (buffer_duration=0)"""
        from app.services.websocket.translation_handler import TranslationHandler

        return TranslationHandler(
            llm_service=mock_llm_service,
            buffer_duration=0,
            source_lang="en",
            target_lang="zh",
        )

    @pytest.fixture
    def handler_throttle_mode(self, mock_llm_service):
        """节流模式处理器 (buffer_duration=6)"""
        from app.services.websocket.translation_handler import TranslationHandler

        return TranslationHandler(
            llm_service=mock_llm_service,
            buffer_duration=6.0,
            source_lang="en",
            target_lang="zh",
        )

    # === 初始化测试 ===

    def test_init_sets_correct_attributes(self, mock_llm_service):
        """测试初始化参数设置"""
        from app.services.websocket.translation_handler import TranslationHandler

        handler = TranslationHandler(
            llm_service=mock_llm_service,
            buffer_duration=5.0,
            source_lang="ja",
            target_lang="en",
            translation_timeout=15.0,
        )

        assert handler.buffer_duration == 5.0
        assert handler.source_lang == "ja"
        assert handler.target_lang == "en"
        assert handler.translation_timeout == 15.0
        assert handler._buffer == ""
        assert handler._last_word_count == 0

    def test_reset_clears_state(self, handler_fast_mode):
        """测试 reset 清空状态"""
        handler_fast_mode._buffer = "some text"
        handler_fast_mode._last_word_count = 10

        handler_fast_mode.reset()

        assert handler_fast_mode._buffer == ""
        assert handler_fast_mode._last_word_count == 0

    # === 极速模式测试 ===

    @pytest.mark.asyncio
    async def test_fast_mode_final_always_translates(self, handler_fast_mode, mock_llm_service):
        """极速模式：final 文本无条件翻译"""
        result = await handler_fast_mode.handle_transcript("Hello world", is_final=True)

        assert result is not None
        assert result["text"] == "翻译结果"
        assert result["is_final"] is True
        mock_llm_service.translate.assert_called_once()

    @pytest.mark.asyncio
    async def test_fast_mode_interim_first_5_words_translates(
        self, handler_fast_mode, mock_llm_service
    ):
        """极速模式：interim 首次达到 5 词触发翻译"""
        # 4 词不触发
        result = await handler_fast_mode.handle_transcript("one two three four", is_final=False)
        assert result is None

        # 5 词触发
        result = await handler_fast_mode.handle_transcript(
            "one two three four five", is_final=False
        )
        assert result is not None
        assert result["is_final"] is False

    @pytest.mark.asyncio
    async def test_fast_mode_interim_5_word_increment(self, handler_fast_mode, mock_llm_service):
        """极速模式：interim 每增加 5 词触发一次翻译"""
        # 第一次：5 词
        await handler_fast_mode.handle_transcript("one two three four five", is_final=False)
        assert handler_fast_mode._last_word_count == 5

        # 9 词不触发 (需要 10)
        result = await handler_fast_mode.handle_transcript(
            "one two three four five six seven eight nine", is_final=False
        )
        assert result is None

        # 10 词触发
        result = await handler_fast_mode.handle_transcript(
            "one two three four five six seven eight nine ten", is_final=False
        )
        assert result is not None
        assert handler_fast_mode._last_word_count == 10

    @pytest.mark.asyncio
    async def test_fast_mode_final_resets_word_count(self, handler_fast_mode, mock_llm_service):
        """极速模式：final 重置 word count"""
        handler_fast_mode._last_word_count = 10

        await handler_fast_mode.handle_transcript("Final text.", is_final=True)

        assert handler_fast_mode._last_word_count == 0

    # === 节流模式测试 ===

    @pytest.mark.asyncio
    async def test_throttle_mode_interim_never_translates(
        self, handler_throttle_mode, mock_llm_service
    ):
        """节流模式：interim 不触发翻译"""
        result = await handler_throttle_mode.handle_transcript(
            "This is interim text", is_final=False
        )

        assert result is None
        mock_llm_service.translate.assert_not_called()

    @pytest.mark.asyncio
    async def test_throttle_mode_accumulates_final(self, handler_throttle_mode):
        """节流模式：累积 final 文本"""
        await handler_throttle_mode.handle_transcript("Hello", is_final=True)
        await handler_throttle_mode.handle_transcript("world", is_final=True)

        assert "Hello" in handler_throttle_mode._buffer
        assert "world" in handler_throttle_mode._buffer

    @pytest.mark.asyncio
    async def test_throttle_mode_flushes_on_punctuation(
        self, handler_throttle_mode, mock_llm_service
    ):
        """节流模式：句末标点触发翻译"""
        await handler_throttle_mode.handle_transcript("Hello", is_final=True)
        result = await handler_throttle_mode.handle_transcript("world.", is_final=True)

        assert result is not None
        assert handler_throttle_mode._buffer == ""
        mock_llm_service.translate.assert_called_once()

    @pytest.mark.asyncio
    async def test_throttle_mode_flushes_on_50_words(self, handler_throttle_mode, mock_llm_service):
        """节流模式：50 词上限触发翻译"""
        # 累积 49 词
        words_49 = " ".join([f"word{i}" for i in range(49)])
        await handler_throttle_mode.handle_transcript(words_49, is_final=True)

        # 第 50 词触发
        result = await handler_throttle_mode.handle_transcript("word50", is_final=True)

        assert result is not None
        mock_llm_service.translate.assert_called_once()

    @pytest.mark.asyncio
    async def test_throttle_mode_various_punctuation(self, handler_throttle_mode, mock_llm_service):
        """节流模式：各种标点都能触发"""
        punctuations = [".", "!", "?", "。", "！", "？"]

        for _, punct in enumerate(punctuations):
            handler_throttle_mode._buffer = ""
            result = await handler_throttle_mode.handle_transcript(f"Text{punct}", is_final=True)
            assert result is not None, f"Punctuation {punct} should trigger translation"

    # === flush 测试 ===

    @pytest.mark.asyncio
    async def test_flush_translates_remaining_buffer(self, handler_throttle_mode, mock_llm_service):
        """flush 翻译剩余缓冲区"""
        handler_throttle_mode._buffer = "remaining text"

        result = await handler_throttle_mode.flush()

        assert result is not None
        assert result["text"] == "翻译结果"
        assert handler_throttle_mode._buffer == ""

    @pytest.mark.asyncio
    async def test_flush_empty_buffer_returns_none(self, handler_throttle_mode):
        """flush 空缓冲区返回 None"""
        handler_throttle_mode._buffer = ""

        result = await handler_throttle_mode.flush()

        assert result is None

    @pytest.mark.asyncio
    async def test_flush_whitespace_only_returns_none(self, handler_throttle_mode):
        """flush 仅空白缓冲区返回 None"""
        handler_throttle_mode._buffer = "   "

        result = await handler_throttle_mode.flush()

        assert result is None

    # === 错误处理测试 ===

    @pytest.mark.asyncio
    async def test_translation_timeout_returns_none(self, handler_fast_mode, mock_llm_service):
        """翻译超时返回 None"""
        import asyncio

        async def slow_translate(*args, **kwargs):
            await asyncio.sleep(100)
            return "result"

        mock_llm_service.translate = slow_translate
        handler_fast_mode.translation_timeout = 0.01

        result = await handler_fast_mode.handle_transcript("Hello", is_final=True)

        assert result is None

    @pytest.mark.asyncio
    async def test_translation_error_returns_none(self, handler_fast_mode, mock_llm_service):
        """翻译异常返回 None"""
        mock_llm_service.translate = AsyncMock(side_effect=Exception("API Error"))

        result = await handler_fast_mode.handle_transcript("Hello", is_final=True)

        assert result is None

    @pytest.mark.asyncio
    async def test_empty_text_returns_none(self, handler_fast_mode):
        """空文本返回 None"""
        result = await handler_fast_mode.handle_transcript("", is_final=True)

        assert result is None

    @pytest.mark.asyncio
    async def test_whitespace_text_returns_none(self, handler_fast_mode):
        """纯空白文本返回 None"""
        result = await handler_fast_mode.handle_transcript("   ", is_final=True)

        assert result is None

    # === 上下文测试 ===

    @pytest.mark.asyncio
    async def test_context_updated_on_final(self, handler_fast_mode, mock_llm_service):
        """final 翻译后更新上下文"""
        await handler_fast_mode.handle_transcript("First sentence.", is_final=True)

        assert handler_fast_mode._last_context == "First sentence."

    @pytest.mark.asyncio
    async def test_context_passed_to_translate(self, handler_fast_mode, mock_llm_service):
        """翻译时传递上下文"""
        handler_fast_mode._last_context = "Previous context"

        await handler_fast_mode.handle_transcript("New text", is_final=True)

        mock_llm_service.translate.assert_called_with(
            "New text",
            source_lang="en",
            target_lang="zh",
            context="Previous context",
        )
