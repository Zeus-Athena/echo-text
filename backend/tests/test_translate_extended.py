"""
Translate API Extended Tests
扩展翻译 API 测试覆盖
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


@pytest.fixture
def mock_user():
    u = MagicMock()
    u.id = uuid4()
    return u


@pytest.fixture
def mock_db():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    db.execute.return_value = mock_result
    return db


class TestGetTranslationHistory:
    """测试获取翻译历史"""

    @pytest.mark.asyncio
    async def test_get_translation_history_empty(self, mock_user, mock_db):
        """测试空历史记录"""
        from app.api.v1.translate import get_translation_history

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await get_translation_history(current_user=mock_user, db=mock_db)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_translation_history_with_limit(self, mock_user, mock_db):
        """测试带限制的历史记录"""
        from app.api.v1.translate import get_translation_history

        mock_history = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_history
        mock_db.execute.return_value = mock_result

        result = await get_translation_history(limit=10, current_user=mock_user, db=mock_db)

        assert len(result) == 2


class TestGetDictionaryHistory:
    """测试获取字典历史"""

    @pytest.mark.asyncio
    async def test_get_dictionary_history_empty(self, mock_user, mock_db):
        """测试空字典历史"""
        from app.api.v1.translate import get_dictionary_history

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await get_dictionary_history(current_user=mock_user, db=mock_db)

        assert result == []


class TestGetVocabulary:
    """测试获取生词本"""

    @pytest.mark.asyncio
    async def test_get_vocabulary_empty(self, mock_user, mock_db):
        """测试空生词本"""
        from app.api.v1.translate import get_vocabulary

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await get_vocabulary(current_user=mock_user, db=mock_db)

        assert result == []


class TestAddToVocabulary:
    """测试添加到生词本"""

    @pytest.mark.asyncio
    async def test_add_to_vocabulary_new_word(self, mock_user, mock_db):
        """测试添加新单词"""
        from app.api.v1.translate import add_to_vocabulary
        from app.schemas.translation import AddToVocabularyRequest

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        request = AddToVocabularyRequest(word="hello", language="en")
        result = await add_to_vocabulary(request, current_user=mock_user, db=mock_db)

        assert result["message"] == "Word added to vocabulary"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_to_vocabulary_existing_word(self, mock_user, mock_db):
        """测试添加已存在的单词"""
        from app.api.v1.translate import add_to_vocabulary
        from app.schemas.translation import AddToVocabularyRequest

        mock_existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing
        mock_db.execute.return_value = mock_result

        request = AddToVocabularyRequest(word="hello", language="en")
        result = await add_to_vocabulary(request, current_user=mock_user, db=mock_db)

        assert result["message"] == "Word already in vocabulary"
        mock_db.add.assert_not_called()


class TestRemoveFromVocabulary:
    """测试从生词本移除"""

    @pytest.mark.asyncio
    async def test_remove_from_vocabulary_success(self, mock_user, mock_db):
        """测试成功移除单词"""
        from app.api.v1.translate import remove_from_vocabulary

        mock_entry = MagicMock()
        mock_entry.is_in_vocabulary = True
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_entry
        mock_db.execute.return_value = mock_result

        result = await remove_from_vocabulary(word="hello", current_user=mock_user, db=mock_db)

        assert result["message"] == "Word removed from vocabulary"
        assert mock_entry.is_in_vocabulary is False
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_from_vocabulary_not_found(self, mock_user, mock_db):
        """测试移除不存在的单词"""
        from app.api.v1.translate import remove_from_vocabulary

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await remove_from_vocabulary(word="unknown", current_user=mock_user, db=mock_db)

        assert result["message"] == "Word removed from vocabulary"


class TestGetTTSVoices:
    """测试获取 TTS 语音列表"""

    @pytest.mark.asyncio
    async def test_get_tts_voices(self):
        """测试获取语音列表"""
        from app.api.v1.translate import get_tts_voices

        result = await get_tts_voices()

        # 返回的是列表
        assert isinstance(result, list)
        assert len(result) > 0
        # 检查 voice 结构
        assert "id" in result[0]
        assert "name" in result[0]
