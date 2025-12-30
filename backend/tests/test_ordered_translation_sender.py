"""
Tests for OrderedTranslationSender
顺序发送翻译单元测试
"""

import pytest

from app.services.websocket.ordered_translation_sender import OrderedTranslationSender
from app.services.websocket.translation_handler import TranslationResult


class TestOrderedTranslationSender:
    """OrderedTranslationSender 单元测试"""

    @pytest.fixture
    def sent_results(self):
        """记录发送的结果"""
        return []

    @pytest.fixture
    def sender(self, sent_results):
        """创建 sender 实例"""

        async def send_callback(result):
            sent_results.append(result)

        return OrderedTranslationSender(send_callback)

    def make_result(
        self, index: int, text: str = "", segment_id: str = "seg-1"
    ) -> TranslationResult:
        """创建测试用的 TranslationResult"""
        return TranslationResult(
            text=text or f"Translation {index}",
            segment_id=segment_id,
            sentence_index=index,
        )

    # === 基础功能测试 ===

    @pytest.mark.asyncio
    async def test_single_result_sent_immediately(self, sender, sent_results):
        """单个结果（index=0）立即发送"""
        result = self.make_result(0)
        await sender.on_translation_complete(result)

        assert len(sent_results) == 1
        assert sent_results[0].sentence_index == 0

    @pytest.mark.asyncio
    async def test_sequential_results_sent_in_order(self, sender, sent_results):
        """顺序到达的结果按顺序发送"""
        await sender.on_translation_complete(self.make_result(0))
        await sender.on_translation_complete(self.make_result(1))
        await sender.on_translation_complete(self.make_result(2))

        assert len(sent_results) == 3
        assert [r.sentence_index for r in sent_results] == [0, 1, 2]

    # === 乱序到达测试 ===

    @pytest.mark.asyncio
    async def test_out_of_order_waits_for_previous(self, sender, sent_results):
        """乱序到达时等待前面的结果"""
        # index=1 先到达，应该等待
        await sender.on_translation_complete(self.make_result(1))
        assert len(sent_results) == 0
        assert sender.has_pending()
        assert sender.pending_count == 1

        # index=0 到达，应该发送 0 和 1
        await sender.on_translation_complete(self.make_result(0))
        assert len(sent_results) == 2
        assert [r.sentence_index for r in sent_results] == [0, 1]
        assert not sender.has_pending()

    @pytest.mark.asyncio
    async def test_complex_out_of_order(self, sender, sent_results):
        """复杂的乱序场景"""
        # 2, 4, 0, 1, 3 的顺序到达
        await sender.on_translation_complete(self.make_result(2))
        assert len(sent_results) == 0

        await sender.on_translation_complete(self.make_result(4))
        assert len(sent_results) == 0

        await sender.on_translation_complete(self.make_result(0))
        assert len(sent_results) == 1  # 只发 0，1 还没到

        await sender.on_translation_complete(self.make_result(1))
        assert len(sent_results) == 3  # 发 1, 2

        await sender.on_translation_complete(self.make_result(3))
        assert len(sent_results) == 5  # 发 3, 4
        assert [r.sentence_index for r in sent_results] == [0, 1, 2, 3, 4]

    # === Flush 测试 ===

    @pytest.mark.asyncio
    async def test_flush_all_sends_pending(self, sender, sent_results):
        """flush_all 发送所有待发送的结果"""
        await sender.on_translation_complete(self.make_result(2))
        await sender.on_translation_complete(self.make_result(1))
        assert len(sent_results) == 0

        await sender.flush_all()
        assert len(sent_results) == 2
        assert [r.sentence_index for r in sent_results] == [1, 2]  # 按顺序发送
        assert not sender.has_pending()

    @pytest.mark.asyncio
    async def test_flush_all_empty(self, sender, sent_results):
        """flush_all 在空状态下不报错"""
        await sender.flush_all()
        assert len(sent_results) == 0

    # === Reset 测试 ===

    @pytest.mark.asyncio
    async def test_reset_clears_state(self, sender, sent_results):
        """reset 清空所有状态"""
        await sender.on_translation_complete(self.make_result(1))
        assert sender.has_pending()

        sender.reset()
        assert not sender.has_pending()
        assert sender.next_to_send == 0

        # 重置后 index=0 正常发送
        await sender.on_translation_complete(self.make_result(0))
        assert len(sent_results) == 1

    # === 边界情况 ===

    @pytest.mark.asyncio
    async def test_duplicate_index_overwrites(self, sender, sent_results):
        """重复的 index 会覆盖（取最新的）"""
        await sender.on_translation_complete(self.make_result(1, "First"))
        await sender.on_translation_complete(self.make_result(1, "Second"))  # 覆盖

        await sender.on_translation_complete(self.make_result(0))
        assert len(sent_results) == 2
        assert sent_results[1].text == "Second"

    @pytest.mark.asyncio
    async def test_different_segment_ids(self, sender, sent_results):
        """不同 segment_id 的结果（正常通过，顺序由 index 决定）"""
        await sender.on_translation_complete(self.make_result(0, segment_id="seg-1"))
        await sender.on_translation_complete(
            self.make_result(1, segment_id="seg-2")
        )  # 不同 segment

        assert len(sent_results) == 2
        assert sent_results[0].segment_id == "seg-1"
        assert sent_results[1].segment_id == "seg-2"
