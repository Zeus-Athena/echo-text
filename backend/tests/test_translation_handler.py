"""
Tests for websocket/translation_handler.py
翻译处理器单元测试 - 适配新的时间间隔节流逻辑
"""

import time
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
        """节流模式处理器 (buffer_duration=6, rpm_limit=20)"""
        from app.services.websocket.translation_handler import TranslationHandler

        return TranslationHandler(
            llm_service=mock_llm_service,
            buffer_duration=6.0,
            source_lang="en",
            target_lang="zh",
            rpm_limit=20,
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
            rpm_limit=30,
        )

        assert handler.buffer_duration == 5.0
        assert handler.source_lang == "ja"
        assert handler.target_lang == "en"
        assert handler.translation_timeout == 15.0
        assert handler.rpm_limit == 30
        assert handler.refill_rate == 30 / 60.0  # 令牌桶回血速率

    def test_init_default_rpm_limit(self, mock_llm_service):
        """测试默认 RPM 限制 (新默认值为 100)"""
        from app.services.websocket.translation_handler import TranslationHandler

        handler = TranslationHandler(
            llm_service=mock_llm_service,
            buffer_duration=5.0,
        )

        assert handler.rpm_limit == 100  # 新默认值
        assert handler.refill_rate == 100 / 60.0

    def test_reset_clears_state(self, handler_fast_mode):
        """测试 reset 清空状态 (令牌桶重置)"""
        handler_fast_mode.tokens = 0  # 耗尽令牌
        handler_fast_mode._last_context = "some context"

        handler_fast_mode.reset()

        assert handler_fast_mode.tokens == float(handler_fast_mode.capacity)  # 桶满
        assert handler_fast_mode._last_context == ""

    # === 极速模式测试 ===

    @pytest.mark.asyncio
    async def test_fast_mode_final_always_translates(self, handler_fast_mode, mock_llm_service):
        """极速模式：final 文本无条件翻译"""
        result = await handler_fast_mode.handle_transcript("Hello world", is_final=True)

        assert result
        assert result[0]["text"] == "翻译结果"
        assert result[0]["is_final"] is True
        mock_llm_service.translate.assert_called_once()

    @pytest.mark.asyncio
    async def test_fast_mode_interim_never_translates(self, handler_fast_mode, mock_llm_service):
        """极速模式：interim 不触发翻译"""
        result = await handler_fast_mode.handle_transcript(
            "one two three four five", is_final=False
        )
        assert result == []
        mock_llm_service.translate.assert_not_called()

    @pytest.mark.asyncio
    async def test_fast_mode_preserves_transcript_id(self, handler_fast_mode, mock_llm_service):
        """极速模式：保留 transcript_id"""
        result = await handler_fast_mode.handle_transcript(
            "Hello", is_final=True, transcript_id="test-id-123"
        )

        assert result[0]["transcript_id"] == "test-id-123"

    # === 节流模式测试 ===

    @pytest.mark.asyncio
    async def test_throttle_mode_interim_never_translates(
        self, handler_throttle_mode, mock_llm_service
    ):
        """节流模式：interim 不触发翻译"""
        result = await handler_throttle_mode.handle_transcript(
            "This is interim text", is_final=False
        )

        assert result == []
        mock_llm_service.translate.assert_not_called()

    @pytest.mark.asyncio
    async def test_throttle_mode_translates_each_final_separately(
        self, handler_throttle_mode, mock_llm_service
    ):
        """节流模式：每个 final 单独翻译，保留各自的 transcript_id"""
        # 第一次翻译（无需等待，因为是首次）
        result1 = await handler_throttle_mode.handle_transcript(
            "Hello", is_final=True, transcript_id="id-1"
        )
        assert result1
        assert result1[0]["transcript_id"] == "id-1"

        # 第二次翻译（需要等待间隔）
        # 模拟时间已过足够间隔
        handler_throttle_mode._last_request_time = time.time() - 10

        result2 = await handler_throttle_mode.handle_transcript(
            "World", is_final=True, transcript_id="id-2"
        )
        assert result2
        assert result2[0]["transcript_id"] == "id-2"

        # 验证两次独立调用
        assert mock_llm_service.translate.call_count == 2

    @pytest.mark.asyncio
    async def test_throttle_mode_respects_rate_limit(self, handler_throttle_mode, mock_llm_service):
        """节流模式：遵守令牌桶限速 (首次请求消耗令牌后需等待)"""
        # 令牌桶初始满：10 个令牌，RPM=20 -> refill_rate = 0.333/s
        # 快速连续调用会消耗令牌，之后需等待

        # 耗尽所有令牌
        handler_throttle_mode.tokens = 0.0
        handler_throttle_mode.last_update = __import__("time").monotonic()

        import time

        start_time = time.time()

        # 此时令牌为 0，需要等待
        await handler_throttle_mode.handle_transcript("Hello", is_final=True)

        elapsed = time.time() - start_time

        # 由于令牌为 0，需等待约 3 秒 (60/20 = 3s for 1 token)
        assert elapsed >= 2.5  # 允许一些误差

    @pytest.mark.asyncio
    async def test_throttle_mode_no_wait_on_first_request(
        self, handler_throttle_mode, mock_llm_service
    ):
        """节流模式：首次请求无需等待"""
        handler_throttle_mode._last_request_time = 0.0

        start_time = time.time()
        await handler_throttle_mode.handle_transcript("Hello", is_final=True)
        elapsed = time.time() - start_time

        # 首次请求应该立即执行（不超过 0.5 秒）
        assert elapsed < 0.5

    @pytest.mark.asyncio
    async def test_throttle_mode_updates_last_update_time(
        self, handler_throttle_mode, mock_llm_service
    ):
        """节流模式：更新最后更新时间 (令牌桶)"""
        old_update = handler_throttle_mode.last_update

        await handler_throttle_mode.handle_transcript("Hello", is_final=True)

        # last_update 应该被更新
        assert handler_throttle_mode.last_update >= old_update

    # === flush 测试 ===

    @pytest.mark.asyncio
    async def test_flush_returns_empty_list(self, handler_throttle_mode):
        """新逻辑下 flush 返回空列表（每个 ID 已单独处理）"""
        result = await handler_throttle_mode.flush()

        assert result == []

    # === 错误处理测试 ===

    @pytest.mark.asyncio
    async def test_translation_timeout_returns_none(self, handler_fast_mode, mock_llm_service):
        """翻译超时返回空列表"""
        import asyncio

        async def slow_translate(*args, **kwargs):
            await asyncio.sleep(100)
            return "result"

        mock_llm_service.translate = slow_translate
        handler_fast_mode.translation_timeout = 0.01

        result = await handler_fast_mode.handle_transcript("Hello", is_final=True)

        assert result == []

    @pytest.mark.asyncio
    async def test_translation_error_returns_none(self, handler_fast_mode, mock_llm_service):
        """翻译异常返回空列表"""
        mock_llm_service.translate = AsyncMock(side_effect=Exception("API Error"))

        result = await handler_fast_mode.handle_transcript("Hello", is_final=True)

        assert result == []

    @pytest.mark.asyncio
    async def test_empty_text_returns_none(self, handler_fast_mode):
        """空文本返回空列表"""
        result = await handler_fast_mode.handle_transcript("", is_final=True)

        assert result == []

    @pytest.mark.asyncio
    async def test_whitespace_text_returns_none(self, handler_fast_mode):
        """纯空白文本返回空列表"""
        result = await handler_fast_mode.handle_transcript("   ", is_final=True)

        assert result == []

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


class TestTokenBucketRPMControl:
    """令牌桶 RPM 控制专项测试"""

    @pytest.fixture
    def mock_llm_service(self):
        service = MagicMock()
        service.translate = AsyncMock(return_value="翻译结果")
        return service

    @pytest.mark.asyncio
    async def test_rpm_20_refill_rate(self, mock_llm_service):
        """RPM=20 对应 refill_rate = 0.333/s"""
        from app.services.websocket.translation_handler import TranslationHandler

        handler = TranslationHandler(
            llm_service=mock_llm_service,
            buffer_duration=1.0,
            rpm_limit=20,
        )

        assert abs(handler.refill_rate - 20 / 60.0) < 0.001

    @pytest.mark.asyncio
    async def test_rpm_60_refill_rate(self, mock_llm_service):
        """RPM=60 对应 refill_rate = 1.0/s"""
        from app.services.websocket.translation_handler import TranslationHandler

        handler = TranslationHandler(
            llm_service=mock_llm_service,
            buffer_duration=1.0,
            rpm_limit=60,
        )

        assert abs(handler.refill_rate - 1.0) < 0.001

    @pytest.mark.asyncio
    async def test_bucket_allows_burst(self, mock_llm_service):
        """令牌桶允许突发请求"""
        from app.services.websocket.translation_handler import TranslationHandler

        handler = TranslationHandler(
            llm_service=mock_llm_service,
            rpm_limit=60,  # 1 token/s
        )
        # 初始桶满 (10 tokens)

        import time

        start = time.time()
        # 快速连续 5 次请求
        for i in range(5):
            await handler.handle_transcript(f"Text {i}", is_final=True)
        elapsed = time.time() - start

        # 由于桶满，应该无需等待（<1s）
        assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_custom_capacity_1(self, mock_llm_service):
        """容量=1 时只允许 1 次突发"""
        from app.services.websocket.translation_handler import TranslationHandler

        handler = TranslationHandler(
            llm_service=mock_llm_service,
            rpm_limit=60,
            capacity=1,  # 只允许 1 次突发
        )
        assert handler.capacity == 1

        # 第一次请求立即通过
        import time

        start = time.time()
        await handler.handle_transcript("Text 0", is_final=True)
        elapsed_first = time.time() - start
        assert elapsed_first < 0.5  # 应该立即

        # 耗尽令牌后，第二次需要等待
        handler.tokens = 0.0
        handler.last_update = time.monotonic()
        start = time.time()
        await handler.handle_transcript("Text 1", is_final=True)
        elapsed_second = time.time() - start
        assert elapsed_second >= 0.9  # 等待约 1 秒

    @pytest.mark.asyncio
    async def test_custom_capacity_30(self, mock_llm_service):
        """容量=30 时允许 30 次突发"""
        from app.services.websocket.translation_handler import TranslationHandler

        handler = TranslationHandler(
            llm_service=mock_llm_service,
            rpm_limit=60,
            capacity=30,
        )
        assert handler.capacity == 30
        assert handler.tokens == 30.0  # 初始桶满

    @pytest.mark.asyncio
    async def test_capacity_bounds(self, mock_llm_service):
        """边界值校验：capacity < 1 或 > 100"""
        from app.services.websocket.translation_handler import TranslationHandler

        handler_low = TranslationHandler(
            llm_service=mock_llm_service,
            rpm_limit=60,
            capacity=0,  # 无效值
        )
        assert handler_low.capacity == 1  # 应被修正为 1

        handler_high = TranslationHandler(
            llm_service=mock_llm_service,
            rpm_limit=60,
            capacity=999,  # 超过上限
        )
        assert handler_high.capacity == 100  # 应被修正为 100


class TestSingleIDTranslation:
    """单 ID 翻译测试 - 验证错位问题已修复"""

    @pytest.fixture
    def mock_llm_service(self):
        service = MagicMock()
        service.translate = AsyncMock(return_value="翻译结果")
        return service

    @pytest.mark.asyncio
    async def test_each_transcript_gets_correct_id(self, mock_llm_service):
        """每个转录获得正确的 transcript_id"""
        from app.services.websocket.translation_handler import TranslationHandler

        handler = TranslationHandler(
            llm_service=mock_llm_service,
            buffer_duration=1.0,
            rpm_limit=600,  # 高 RPM 减少测试等待
        )

        results = []

        for i in range(3):
            result = await handler.handle_transcript(
                f"Sentence {i}",
                is_final=True,
                transcript_id=f"id-{i}",
            )
            if result:
                results.extend(result)

        # 每个结果应该有对应的 ID
        assert len(results) == 3
        assert results[0]["transcript_id"] == "id-0"
        assert results[1]["transcript_id"] == "id-1"
        assert results[2]["transcript_id"] == "id-2"

    @pytest.mark.asyncio
    async def test_no_id_mixing(self, mock_llm_service):
        """验证不会发生 ID 混淆"""
        from app.services.websocket.translation_handler import TranslationHandler

        handler = TranslationHandler(
            llm_service=mock_llm_service,
            buffer_duration=1.0,
            rpm_limit=600,
        )

        # 发送多个不同 ID 的转录
        ids_sent = ["uuid-aaa", "uuid-bbb", "uuid-ccc"]
        ids_received = []

        for tid in ids_sent:
            result = await handler.handle_transcript(
                "Some text",
                is_final=True,
                transcript_id=tid,
            )
            if result:
                ids_received.append(result[0]["transcript_id"])

        # 接收到的 ID 应该与发送的完全一致
        assert ids_received == ids_sent


class TestTranslateSentenceAPI:
    """新 translate_sentence API 测试"""

    @pytest.fixture
    def mock_llm_service(self):
        service = MagicMock()
        service.translate = AsyncMock(return_value="翻译结果")
        return service

    @pytest.fixture
    def handler(self, mock_llm_service):
        from app.services.websocket.translation_handler import TranslationHandler

        return TranslationHandler(
            llm_service=mock_llm_service,
            source_lang="en",
            target_lang="zh",
            rpm_limit=600,  # 高 RPM 减少测试等待
        )

    @pytest.mark.asyncio
    async def test_translate_sentence_returns_result(self, handler, mock_llm_service):
        """translate_sentence 返回正确的结果"""
        from app.services.websocket.sentence_builder import SentenceToTranslate

        sentence = SentenceToTranslate(
            text="Hello world.",
            segment_id="seg-123",
            sentence_index=0,
        )

        result = await handler.translate_sentence(sentence)

        assert result.text == "翻译结果"
        assert result.segment_id == "seg-123"
        assert result.sentence_index == 0
        assert result.is_final is True
        assert result.error is False

    @pytest.mark.asyncio
    async def test_translate_sentence_preserves_segment_id(self, handler, mock_llm_service):
        """translate_sentence 保留 segment_id"""
        from app.services.websocket.sentence_builder import SentenceToTranslate

        sentence = SentenceToTranslate(
            text="Test.",
            segment_id="unique-segment-id",
            sentence_index=5,
        )

        result = await handler.translate_sentence(sentence)

        assert result.segment_id == "unique-segment-id"
        assert result.sentence_index == 5

    @pytest.mark.asyncio
    async def test_translate_sentence_updates_context(self, handler, mock_llm_service):
        """translate_sentence 更新上下文"""
        from app.services.websocket.sentence_builder import SentenceToTranslate

        sentence = SentenceToTranslate(
            text="First sentence.",
            segment_id="seg-1",
            sentence_index=0,
        )

        await handler.translate_sentence(sentence)

        assert handler._last_context == "First sentence."

    @pytest.mark.asyncio
    async def test_translate_sentence_timeout_returns_error(self, handler, mock_llm_service):
        """translate_sentence 超时返回错误结果"""
        import asyncio

        from app.services.websocket.sentence_builder import SentenceToTranslate

        async def slow_translate(*args, **kwargs):
            await asyncio.sleep(100)
            return "result"

        mock_llm_service.translate = slow_translate
        handler.translation_timeout = 0.01

        sentence = SentenceToTranslate(
            text="Will timeout.",
            segment_id="seg-1",
            sentence_index=0,
        )

        result = await handler.translate_sentence(sentence)

        assert result.error is True
        assert result.text == "[翻译超时]"
        assert result.segment_id == "seg-1"

    @pytest.mark.asyncio
    async def test_translate_sentence_error_returns_error(self, handler, mock_llm_service):
        """translate_sentence 异常返回错误结果"""
        from app.services.websocket.sentence_builder import SentenceToTranslate

        mock_llm_service.translate = AsyncMock(side_effect=Exception("API Error"))

        sentence = SentenceToTranslate(
            text="Will fail.",
            segment_id="seg-1",
            sentence_index=0,
        )

        result = await handler.translate_sentence(sentence)

        assert result.error is True
        assert result.text == "[翻译失败]"

    @pytest.mark.asyncio
    async def test_translate_sentence_empty_text(self, handler):
        """translate_sentence 空文本返回错误"""
        from app.services.websocket.sentence_builder import SentenceToTranslate

        sentence = SentenceToTranslate(
            text="",
            segment_id="seg-1",
            sentence_index=0,
        )

        result = await handler.translate_sentence(sentence)

        assert result.error is True
        assert result.text == ""

    @pytest.mark.asyncio
    async def test_translate_sentence_respects_rate_limit(self, handler, mock_llm_service):
        """translate_sentence 遵守令牌桶限速"""
        from app.services.websocket.sentence_builder import SentenceToTranslate

        # 设置 RPM=60 (1 token/s) 并耗尽令牌
        handler.rpm_limit = 60
        handler.refill_rate = 1.0
        handler.tokens = 0.0  # 耗尽
        handler.last_update = __import__("time").monotonic()

        sentence1 = SentenceToTranslate(text="First.", segment_id="seg-1", sentence_index=0)

        import time

        start_time = time.time()
        await handler.translate_sentence(sentence1)
        elapsed = time.time() - start_time

        # 由于令牌为 0，需等待约 1 秒
        assert elapsed >= 0.9
