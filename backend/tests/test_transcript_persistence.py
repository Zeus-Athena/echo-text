"""
实时转录入库测试
Test real-time transcript persistence to database
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_append_transcript_creates_new_record():
    """验证：首次追加创建新 Transcript 记录"""
    # Mock database session
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # No existing transcript
    mock_db.execute.return_value = mock_result

    recording_id = uuid4()

    # Import and call
    with patch("app.api.v1.ws_v2.select"):
        from app.api.v1.ws_v2 import append_transcript_to_db

        await append_transcript_to_db(mock_db, recording_id, "Hello world", 0, 1.5)

    # Should add new transcript
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_append_transcript_updates_existing_record():
    """验证：追加到已有 Transcript 记录"""
    # Create mock existing transcript
    mock_transcript = MagicMock()
    mock_transcript.full_text = "Hello"
    mock_transcript.segments = [{"text": "Hello", "start": 0, "end": 1}]

    # Mock database session
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_transcript
    mock_db.execute.return_value = mock_result

    recording_id = uuid4()

    with patch("app.api.v1.ws_v2.select"):
        from app.api.v1.ws_v2 import append_transcript_to_db

        await append_transcript_to_db(mock_db, recording_id, " world", 1, 2)

    # Should update existing transcript
    assert "world" in mock_transcript.full_text
    assert len(mock_transcript.segments) == 2
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_append_transcript_handles_none_recording_id():
    """验证：recording_id 为 None 时跳过入库"""
    mock_db = AsyncMock()

    with patch("app.api.v1.ws_v2.select"):
        from app.api.v1.ws_v2 import append_transcript_to_db

        await append_transcript_to_db(mock_db, None, "test", 0, 1)

    # Should not touch database
    mock_db.execute.assert_not_called()
    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_append_transcript_handles_db_error():
    """验证：数据库错误不会导致崩溃"""
    mock_db = AsyncMock()
    mock_db.commit.side_effect = Exception("DB Connection Lost")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    recording_id = uuid4()

    with patch("app.api.v1.ws_v2.select"):
        from app.api.v1.ws_v2 import append_transcript_to_db

        # Should not raise
        await append_transcript_to_db(mock_db, recording_id, "test", 0, 1)
