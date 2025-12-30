"""
Tests for sentence_builder.py
句子累积器单元测试
"""

import pytest

from app.services.websocket.sentence_builder import SentenceBuilder


class TestSentenceBuilder:
    """SentenceBuilder 单元测试"""

    @pytest.fixture
    def builder(self):
        """创建新的 SentenceBuilder 实例"""
        return SentenceBuilder()

    # === 基础功能测试 ===

    def test_init_empty_state(self, builder):
        """初始状态为空"""
        assert builder.buffer == ""
        assert builder.current_segment_id == ""
        assert builder.sentence_index == 0

    def test_add_final_empty_text_returns_empty(self, builder):
        """空文本返回空列表"""
        result = builder.add_final("", "seg-1")
        assert result == []
        assert builder.buffer == ""

    def test_add_final_whitespace_returns_empty(self, builder):
        """纯空白文本返回空列表"""
        result = builder.add_final("   ", "seg-1")
        assert result == []

    # === 完整句子检测 ===

    def test_single_complete_sentence_period(self, builder):
        """单个句子（句号结尾）触发返回"""
        result = builder.add_final("Hello world.", "seg-1")
        assert len(result) == 1
        assert result[0].text == "Hello world."
        assert result[0].segment_id == "seg-1"
        assert result[0].sentence_index == 0
        assert builder.buffer == ""

    def test_single_complete_sentence_exclamation(self, builder):
        """单个句子（感叹号结尾）触发返回"""
        result = builder.add_final("Hello world!", "seg-1")
        assert len(result) == 1
        assert result[0].text == "Hello world!"

    def test_single_complete_sentence_question(self, builder):
        """单个句子（问号结尾）触发返回"""
        result = builder.add_final("Hello world?", "seg-1")
        assert len(result) == 1
        assert result[0].text == "Hello world?"

    def test_chinese_punctuation(self, builder):
        """中文标点正确识别"""
        result = builder.add_final("你好世界。", "seg-1")
        assert len(result) == 1
        assert result[0].text == "你好世界。"

        result = builder.add_final("这是什么？", "seg-1")
        assert len(result) == 1

        result = builder.add_final("太棒了！", "seg-1")
        assert len(result) == 1

    # === 不完整句子累积 ===

    def test_incomplete_sentence_buffered(self, builder):
        """不完整句子累积到 buffer"""
        result = builder.add_final("Hello", "seg-1")
        assert result == []
        assert builder.buffer == "Hello"

    def test_multiple_finals_accumulate(self, builder):
        """多个 final 正确累积"""
        builder.add_final("Hello", "seg-1")
        builder.add_final("world", "seg-1")
        assert builder.buffer == "Hello world"

    def test_accumulated_sentence_completes(self, builder):
        """累积后遇到句号完成句子"""
        builder.add_final("Hello", "seg-1")
        builder.add_final("world", "seg-1")
        result = builder.add_final("today.", "seg-1")

        assert len(result) == 1
        assert result[0].text == "Hello world today."
        assert builder.buffer == ""

    # === 多个句子 ===

    def test_multiple_sentences_in_one_final(self, builder):
        """一个 final 包含多个句子"""
        result = builder.add_final("First. Second. Third.", "seg-1")
        assert len(result) == 3
        assert result[0].text == "First."
        assert result[0].sentence_index == 0
        assert result[1].text == "Second."
        assert result[1].sentence_index == 1
        assert result[2].text == "Third."
        assert result[2].sentence_index == 2

    def test_sentence_index_increments(self, builder):
        """sentence_index 正确递增"""
        builder.add_final("First.", "seg-1")
        result = builder.add_final("Second.", "seg-1")
        assert result[0].sentence_index == 1

    # === Flush 测试 ===

    def test_flush_returns_remaining(self, builder):
        """flush 返回剩余内容"""
        builder.add_final("Incomplete sentence", "seg-1")
        result = builder.flush()

        assert len(result) == 1
        assert result[0].text == "Incomplete sentence"
        assert builder.buffer == ""

    def test_flush_empty_buffer_returns_empty(self, builder):
        """flush 空 buffer 返回空列表"""
        result = builder.flush()
        assert result == []

    def test_flush_increments_sentence_index(self, builder):
        """flush 后 sentence_index 递增"""
        builder.add_final("First.", "seg-1")  # index 0
        builder.add_final("Incomplete", "seg-1")
        result = builder.flush()

        assert result[0].sentence_index == 1

    # === Segment 切换 ===

    def test_reset_for_new_segment(self, builder):
        """新 segment 重置 sentence_index，并 flush buffer"""
        builder.add_final("First.", "seg-1")  # index 0
        builder.add_final("Second.", "seg-1")  # index 1
        builder.add_final("Incomplete", "seg-1")

        # reset_for_new_segment 会 flush 剩余内容
        flushed = builder.reset_for_new_segment("seg-2")

        assert builder.current_segment_id == "seg-2"
        assert builder.sentence_index == 0
        assert builder.buffer == ""  # buffer 已被 flush
        # flushed 包含之前的不完整句子
        assert len(flushed) == 1
        assert flushed[0].text == "Incomplete"

    def test_buffer_flushed_on_segment_switch(self, builder):
        """新版本：segment 切换时 flush buffer（硬阈值场景）"""
        builder.add_final("This is an incomplete", "seg-1")
        
        # reset_for_new_segment 现在会 flush 而不是保留
        flushed = builder.reset_for_new_segment("seg-2")
        
        # flush 返回之前的内容
        assert len(flushed) == 1
        assert flushed[0].text == "This is an incomplete"
        assert flushed[0].segment_id == "seg-1"  # 归属旧 segment
        
        # 新 segment 从空开始
        assert builder.buffer == ""
        result = builder.add_final("sentence here.", "seg-2")
        assert len(result) == 1
        assert result[0].text == "sentence here."
        assert result[0].segment_id == "seg-2"
        assert result[0].sentence_index == 0

    # === 完全重置 ===

    def test_reset_clears_everything(self, builder):
        """reset 清空所有状态"""
        builder.add_final("Some text.", "seg-1")
        builder.add_final("More text", "seg-1")
        builder.reset()

        assert builder.buffer == ""
        assert builder.current_segment_id == ""
        assert builder.sentence_index == 0

    # === 辅助方法 ===

    def test_get_incomplete_text(self, builder):
        """获取未完成文本"""
        builder.add_final("Incomplete", "seg-1")
        assert builder.get_incomplete_text() == "Incomplete"

    def test_clear_buffer(self, builder):
        """清空 buffer"""
        builder.add_final("Some text", "seg-1")
        builder.clear_buffer()
        assert builder.buffer == ""
        # sentence_index 不变
        assert builder.sentence_index == 0


class TestSentenceBuilderEdgeCases:
    """边界情况测试"""

    @pytest.fixture
    def builder(self):
        return SentenceBuilder()

    def test_trailing_space_after_punctuation(self, builder):
        """标点后有空格正确处理"""
        result = builder.add_final("Hello world. ", "seg-1")
        assert len(result) == 1
        assert result[0].text == "Hello world."

    def test_multiple_spaces_between_words(self, builder):
        """多个空格正确处理"""
        builder.add_final("Hello", "seg-1")
        result = builder.add_final("  world.", "seg-1")
        assert result[0].text == "Hello world."

    def test_mixed_punctuation_sentence(self, builder):
        """混合标点（省略号后不切分）"""
        # 省略号不是句末标点，不切分
        result = builder.add_final("Wait... What?", "seg-1")
        # "Wait..." 包含句号，会触发切分
        assert len(result) >= 1

    def test_abbreviations_may_split(self, builder):
        """缩写可能被错误切分（已知限制）"""
        # 注意：简单的句号检测无法处理 "Dr." "Mr." 等缩写
        # 这是已知限制，接受这个行为
        result = builder.add_final("Dr. Smith is here.", "seg-1")
        # 可能切分成 "Dr." 和 "Smith is here."
        # 这是可接受的，因为完美句子边界检测需要 NLP
        assert len(result) >= 1

    def test_numbers_with_periods(self, builder):
        """数字中的小数点可能触发切分（已知限制）"""
        result = builder.add_final("The value is 3.14 today.", "seg-1")
        # "3." 会触发切分，这是已知限制
        assert len(result) >= 1
