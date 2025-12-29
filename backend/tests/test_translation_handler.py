"""
Tests for websocket/translation_handler.py
翻译处理器单元测试 - 适配新的时间间隔节流逻辑
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

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
        assert handler.min_interval == 2.0  # 60 / 30 = 2s

    def test_init_default_rpm_limit(self, mock_llm_service):
        """测试默认 RPM 限制"""
        from app.services.websocket.translation_handler import TranslationHandler

        handler = TranslationHandler(
            llm_service=mock_llm_service,
            buffer_duration=5.0,
        )

        assert handler.rpm_limit == 20
        assert handler.min_interval == 3.0  # 60 / 20 = 3s

    def test_reset_clears_state(self, handler_fast_mode):
        """测试 reset 清空状态"""
        handler_fast_mode._last_request_time = 100.0
        handler_fast_mode._last_context = "some context"

        handler_fast_mode.reset()

        assert handler_fast_mode._last_request_time == 0.0
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
    async def test_fast_mode_interim_never_translates(
        self, handler_fast_mode, mock_llm_service
    ):
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
    async def test_throttle_mode_respects_min_interval(
        self, handler_throttle_mode, mock_llm_service
    ):
        """节流模式：遵守最小时间间隔"""
        # 设置一个很短的间隔用于测试
        handler_throttle_mode.rpm_limit = 60
        handler_throttle_mode.min_interval = 1.0

        start_time = time.time()

        # 第一次翻译
        await handler_throttle_mode.handle_transcript("Hello", is_final=True)

        # 第二次翻译（应该等待约 1 秒）
        await handler_throttle_mode.handle_transcript("World", is_final=True)

        elapsed = time.time() - start_time

        # 两次翻译之间应该至少有 1 秒间隔
        assert elapsed >= 1.0

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
    async def test_throttle_mode_updates_last_request_time(
        self, handler_throttle_mode, mock_llm_service
    ):
        """节流模式：更新最后请求时间"""
        handler_throttle_mode._last_request_time = 0.0

        await handler_throttle_mode.handle_transcript("Hello", is_final=True)

        assert handler_throttle_mode._last_request_time > 0

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


class TestThrottleModeRPMControl:
    """节流模式 RPM 控制专项测试"""

    @pytest.fixture
    def mock_llm_service(self):
        service = MagicMock()
        service.translate = AsyncMock(return_value="翻译结果")
        return service

    @pytest.mark.asyncio
    async def test_rpm_20_means_3s_interval(self, mock_llm_service):
        """RPM=20 对应 3 秒间隔"""
        from app.services.websocket.translation_handler import TranslationHandler

        handler = TranslationHandler(
            llm_service=mock_llm_service,
            buffer_duration=1.0,
            rpm_limit=20,
        )

        assert handler.min_interval == 3.0

    @pytest.mark.asyncio
    async def test_rpm_30_means_2s_interval(self, mock_llm_service):
        """RPM=30 对应 2 秒间隔"""
        from app.services.websocket.translation_handler import TranslationHandler

        handler = TranslationHandler(
            llm_service=mock_llm_service,
            buffer_duration=1.0,
            rpm_limit=30,
        )

        assert handler.min_interval == 2.0

    @pytest.mark.asyncio
    async def test_rpm_60_means_1s_interval(self, mock_llm_service):
        """RPM=60 对应 1 秒间隔"""
        from app.services.websocket.translation_handler import TranslationHandler

        handler = TranslationHandler(
            llm_service=mock_llm_service,
            buffer_duration=1.0,
            rpm_limit=60,
        )

        assert handler.min_interval == 1.0


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
