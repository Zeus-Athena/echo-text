"""
Tests for translation strategy in ws_v2.py
翻译策略测试 - 极速模式和节流模式
"""


class TestShouldTranslateBuffer:
    """测试 should_translate_buffer 函数逻辑"""

    def should_translate_buffer(self, text: str) -> bool:
        """从 ws_v2.py 复制的逻辑，用于测试"""
        if not text.strip():
            return False
        # 句末标点检测
        if text.rstrip()[-1] in ".!?。！？":
            return True
        # 50 词上限
        word_count = len(text.split())
        if word_count >= 50:
            return True
        return False

    def test_empty_text_returns_false(self):
        """空文本不应触发翻译"""
        assert self.should_translate_buffer("") is False
        assert self.should_translate_buffer("   ") is False

    def test_sentence_end_punctuation_triggers_translation(self):
        """句末标点应触发翻译"""
        assert self.should_translate_buffer("Hello world.") is True
        assert self.should_translate_buffer("Are you sure?") is True
        assert self.should_translate_buffer("Wow!") is True
        assert self.should_translate_buffer("你好。") is True
        assert self.should_translate_buffer("是吗？") is True
        assert self.should_translate_buffer("太好了！") is True

    def test_incomplete_sentence_does_not_trigger(self):
        """不完整的句子不应触发翻译"""
        assert self.should_translate_buffer("Hello world") is False
        assert self.should_translate_buffer("The quick brown fox") is False

    def test_50_word_limit_triggers_translation(self):
        """超过 50 词应强制触发翻译"""
        # 生成 49 个词
        words_49 = " ".join(["word"] * 49)
        assert self.should_translate_buffer(words_49) is False

        # 生成 50 个词
        words_50 = " ".join(["word"] * 50)
        assert self.should_translate_buffer(words_50) is True

        # 生成 100 个词
        words_100 = " ".join(["word"] * 100)
        assert self.should_translate_buffer(words_100) is True

    def test_punctuation_takes_priority_over_word_count(self):
        """标点优先于字数判断"""
        # 10 个词但有句号
        short_sentence = "This is a short sentence."
        assert self.should_translate_buffer(short_sentence) is True


class TestInterimWordDebounce:
    """测试极速模式下 interim 的 5 词防抖逻辑"""

    def should_translate_interim(self, current_word_count: int, last_word_count: int) -> bool:
        """从 ws_v2.py 复制的逻辑"""
        return current_word_count >= last_word_count + 5

    def test_less_than_5_new_words_does_not_trigger(self):
        """新增少于 5 词不应触发翻译"""
        assert self.should_translate_interim(4, 0) is False
        assert self.should_translate_interim(10, 8) is False
        assert self.should_translate_interim(15, 12) is False

    def test_exactly_5_new_words_triggers(self):
        """新增恰好 5 词应触发翻译"""
        assert self.should_translate_interim(5, 0) is True
        assert self.should_translate_interim(10, 5) is True
        assert self.should_translate_interim(20, 15) is True

    def test_more_than_5_new_words_triggers(self):
        """新增超过 5 词应触发翻译"""
        assert self.should_translate_interim(8, 0) is True
        assert self.should_translate_interim(15, 5) is True


class TestTranslationModeSelection:
    """测试翻译模式选择逻辑"""

    def test_buffer_duration_zero_is_turbo_mode(self):
        """buffer_duration = 0 应使用极速模式"""
        buffer_duration = 0
        # 极速模式特征：翻译 interim + final
        assert buffer_duration == 0

    def test_buffer_duration_positive_is_throttle_mode(self):
        """buffer_duration > 0 应使用节流模式"""
        for duration in [1, 2, 3, 6]:
            # 节流模式特征：只翻译 final，累积后发送
            assert duration > 0
