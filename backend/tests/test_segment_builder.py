"""
Tests for segment_builder.py
卡片切分器单元测试
"""

import pytest

from app.services.websocket.segment_builder import SegmentBuilder


class TestSegmentBuilder:
    """SegmentBuilder 单元测试"""

    @pytest.fixture
    def builder(self):
        """创建默认阈值的 SegmentBuilder (soft=30, hard=60)"""
        return SegmentBuilder(soft_threshold=30, hard_threshold=60)

    @pytest.fixture
    def builder_small_thresholds(self):
        """创建小阈值的 SegmentBuilder (soft=5, hard=10) 便于测试"""
        return SegmentBuilder(soft_threshold=5, hard_threshold=10)

    # === 初始化测试 ===

    def test_init_default_values(self, builder):
        """初始化设置正确的默认值"""
        assert builder.soft_threshold == 30
        assert builder.hard_threshold == 60
        assert builder.buffer == ""
        assert builder.start_time == 0.0
        assert builder.end_time == 0.0
        assert builder.current_segment_id != ""

    def test_init_invalid_thresholds(self):
        """软阈值必须小于硬阈值"""
        with pytest.raises(ValueError):
            SegmentBuilder(soft_threshold=60, hard_threshold=30)

        with pytest.raises(ValueError):
            SegmentBuilder(soft_threshold=30, hard_threshold=30)

    def test_segment_id_unique(self):
        """每个实例的 segment_id 唯一"""
        builder1 = SegmentBuilder()
        builder2 = SegmentBuilder()
        assert builder1.current_segment_id != builder2.current_segment_id

    # === 文本累积测试 ===

    def test_add_final_empty_text(self, builder):
        """空文本不累积"""
        seg_id = builder.add_final("", 0.0, 1.0)
        assert builder.buffer == ""
        assert seg_id == builder.current_segment_id

    def test_add_final_single_text(self, builder):
        """单个文本正确累积"""
        seg_id = builder.add_final("Hello world", 0.0, 1.0)
        assert builder.buffer == "Hello world"
        assert builder.start_time == 0.0
        assert builder.end_time == 1.0
        assert seg_id == builder.current_segment_id

    def test_add_final_multiple_texts(self, builder):
        """多个文本正确累积"""
        builder.add_final("Hello", 0.0, 0.5)
        builder.add_final("world", 0.5, 1.0)
        builder.add_final("today", 1.0, 1.5)

        assert builder.buffer == "Hello world today"
        assert builder.start_time == 0.0
        assert builder.end_time == 1.5

    def test_word_count(self, builder):
        """词数统计正确"""
        builder.add_final("Hello world today", 0.0, 1.0)
        assert builder.word_count == 3

    def test_word_count_empty(self, builder):
        """空 buffer 词数为 0"""
        assert builder.word_count == 0

    # === 软阈值切分测试 ===

    def test_no_split_under_soft_threshold(self, builder_small_thresholds):
        """低于软阈值不切分"""
        builder_small_thresholds.add_final("One two three.", 0.0, 1.0)  # 3 词
        result = builder_small_thresholds.check_split()
        assert result is None

    def test_soft_threshold_with_punctuation(self, builder_small_thresholds):
        """超过软阈值 + 句末标点 → 切分"""
        # 5 词 + 句号
        builder_small_thresholds.add_final("One two three four five.", 0.0, 2.0)
        result = builder_small_thresholds.check_split()

        assert result is not None
        assert result.text == "One two three four five."
        assert result.word_count == 5
        assert result.start == 0.0
        assert result.end == 2.0

    def test_soft_threshold_without_punctuation_no_split(self, builder_small_thresholds):
        """超过软阈值但无句末标点 → 不切分"""
        # 5 词，无句号
        builder_small_thresholds.add_final("One two three four five", 0.0, 2.0)
        result = builder_small_thresholds.check_split()
        assert result is None

    def test_soft_threshold_exclamation(self, builder_small_thresholds):
        """感叹号也触发切分"""
        builder_small_thresholds.add_final("One two three four five!", 0.0, 2.0)
        result = builder_small_thresholds.check_split()
        assert result is not None

    def test_soft_threshold_question_mark(self, builder_small_thresholds):
        """问号也触发切分"""
        builder_small_thresholds.add_final("One two three four five?", 0.0, 2.0)
        result = builder_small_thresholds.check_split()
        assert result is not None

    def test_chinese_punctuation_triggers_split(self, builder_small_thresholds):
        """中文标点触发切分"""
        builder_small_thresholds.add_final("一 二 三 四 五。", 0.0, 2.0)
        result = builder_small_thresholds.check_split()
        assert result is not None

    # === 硬阈值切分测试 ===

    def test_hard_threshold_forces_split(self, builder_small_thresholds):
        """超过硬阈值强制切分（无需标点）"""
        # 10 词，无句号
        builder_small_thresholds.add_final(
            "One two three four five six seven eight nine ten", 0.0, 5.0
        )
        result = builder_small_thresholds.check_split()

        assert result is not None
        assert result.word_count == 10

    def test_hard_threshold_overrides_no_punctuation(self, builder_small_thresholds):
        """硬阈值切分不需要标点"""
        text = " ".join(["word"] * 12)  # 12 词
        builder_small_thresholds.add_final(text, 0.0, 6.0)
        result = builder_small_thresholds.check_split()

        assert result is not None
        assert result.word_count == 12

    # === 切分后状态重置测试 ===

    def test_split_resets_buffer(self, builder_small_thresholds):
        """切分后 buffer 清空"""
        builder_small_thresholds.add_final("One two three four five.", 0.0, 2.0)
        builder_small_thresholds.check_split()

        assert builder_small_thresholds.buffer == ""
        assert builder_small_thresholds.word_count == 0

    def test_split_resets_timestamps(self, builder_small_thresholds):
        """切分后时间戳重置"""
        builder_small_thresholds.add_final("One two three four five.", 0.0, 2.0)
        builder_small_thresholds.check_split()

        assert builder_small_thresholds.start_time == 0.0
        assert builder_small_thresholds.end_time == 0.0

    def test_split_generates_new_segment_id(self, builder_small_thresholds):
        """切分后生成新的 segment_id"""
        old_id = builder_small_thresholds.current_segment_id
        builder_small_thresholds.add_final("One two three four five.", 0.0, 2.0)
        builder_small_thresholds.check_split()

        assert builder_small_thresholds.current_segment_id != old_id

    def test_multiple_splits(self, builder_small_thresholds):
        """多次切分正确工作"""
        # 第一次切分
        builder_small_thresholds.add_final("One two three four five.", 0.0, 2.0)
        result1 = builder_small_thresholds.check_split()
        id1 = result1.segment_id

        # 第二次切分
        builder_small_thresholds.add_final("Six seven eight nine ten.", 2.0, 4.0)
        result2 = builder_small_thresholds.check_split()
        id2 = result2.segment_id

        assert id1 != id2
        assert result1.end == 2.0
        assert result2.start == 2.0

    # === 强制切分测试 ===

    def test_force_split_returns_remaining(self, builder):
        """force_split 返回剩余内容"""
        builder.add_final("Incomplete segment", 0.0, 1.0)
        result = builder.force_split()

        assert result is not None
        assert result.text == "Incomplete segment"
        assert builder.buffer == ""

    def test_force_split_empty_returns_none(self, builder):
        """force_split 空 buffer 返回 None"""
        result = builder.force_split()
        assert result is None

    # === 重置测试 ===

    def test_reset_clears_all_state(self, builder):
        """reset 清空所有状态"""
        old_id = builder.current_segment_id
        builder.add_final("Some text", 1.0, 2.0)
        builder.reset()

        assert builder.buffer == ""
        assert builder.start_time == 0.0
        assert builder.end_time == 0.0
        assert builder.current_segment_id != old_id

    # === 调试辅助 ===

    def test_get_current_state(self, builder):
        """获取当前状态"""
        builder.add_final("Hello world", 1.0, 2.0)
        state = builder.get_current_state()

        assert state["buffer"] == "Hello world"
        assert state["word_count"] == 2
        assert state["start_time"] == 1.0
        assert state["end_time"] == 2.0


class TestSegmentBuilderEdgeCases:
    """边界情况测试"""

    @pytest.fixture
    def builder(self):
        return SegmentBuilder(soft_threshold=5, hard_threshold=10)

    def test_exact_soft_threshold(self, builder):
        """恰好等于软阈值 + 标点 → 切分"""
        builder.add_final("One two three four five.", 0.0, 2.0)  # 恰好 5 词
        result = builder.check_split()
        assert result is not None

    def test_one_below_soft_threshold(self, builder):
        """软阈值 -1 + 标点 → 不切分"""
        builder.add_final("One two three four.", 0.0, 2.0)  # 4 词
        result = builder.check_split()
        assert result is None

    def test_exact_hard_threshold(self, builder):
        """恰好等于硬阈值 → 切分"""
        text = " ".join(["word"] * 10)  # 恰好 10 词
        builder.add_final(text, 0.0, 5.0)
        result = builder.check_split()
        assert result is not None

    def test_timestamps_gap_in_finals(self, builder):
        """final 之间有时间间隙"""
        builder.add_final("Hello", 0.0, 0.5)
        builder.add_final("world", 1.0, 1.5)  # 0.5s 间隙

        assert builder.start_time == 0.0
        assert builder.end_time == 1.5

    def test_trailing_spaces_in_text(self, builder):
        """文本有尾随空格"""
        builder.add_final("Hello   ", 0.0, 0.5)
        builder.add_final("  world  ", 0.5, 1.0)

        assert builder.buffer == "Hello world"

    def test_comma_not_trigger_split(self, builder):
        """逗号不触发切分"""
        builder.add_final("One, two, three, four, five,", 0.0, 2.0)
        result = builder.check_split()
        assert result is None  # 5 词 + 逗号，但逗号不是句末标点
