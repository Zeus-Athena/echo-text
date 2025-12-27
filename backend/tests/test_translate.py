"""
Translate API Tests (Stable Only)
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.api.v1.translate import translate_text
from app.schemas.translation import TextTranslateRequest


@pytest.fixture
def mock_user():
    u = MagicMock()
    u.id = uuid4()
    return u


@pytest.mark.asyncio
async def test_translate_text_success(mock_user):
    """测试文本翻译"""
    db = AsyncMock()
    # 正确 mock db.execute().scalar_one_or_none() 返回 None (无自定义 prompt)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result

    req = TextTranslateRequest(text="Hello world", source_lang="en", target_lang="zh")

    with (
        patch("app.api.v1.translate.get_effective_config", new_callable=AsyncMock) as mock_cfg,
        patch("app.api.v1.translate.get_llm_service", new_callable=AsyncMock) as mock_get_llm,
    ):
        mock_cfg.return_value = MagicMock()
        mock_llm = MagicMock()
        mock_llm.translate = AsyncMock(return_value="你好世界")
        mock_llm.model = "gpt-4"
        mock_get_llm.return_value = mock_llm

        res = await translate_text(req, mock_user, db)

        assert res.translated_text == "你好世界"
