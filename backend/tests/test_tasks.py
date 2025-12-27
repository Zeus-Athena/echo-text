"""
Tasks 测试
Test background tasks (Celery/Worker style functions)
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.workers.tasks import process_uploaded_audio_task


@pytest.mark.asyncio
async def test_process_uploaded_audio_task_success():
    """验证音频上传处理任务流程"""
    rec_id = str(uuid4())  # Use string to avoid UUID version compatibility issues

    with (
        patch("app.workers.tasks.async_session") as mock_session_ctx,
        patch("app.workers.tasks.STTService") as MockSTT,
        patch("app.workers.tasks.LLMService") as MockLLM,
    ):
        mock_db = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_db

        mock_rec = MagicMock()
        mock_rec.id = uuid4()  # The obj ID can be UUID
        mock_rec.status = "uploaded"
        mock_rec.audio_oid = 1
        mock_rec.audio_blob_id = 1

        # Mock DB returns
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [
            mock_rec,  # Recording
            MagicMock(),  # UserConfig
            None,  # existing transcript
            None,  # existing translation
        ]
        mock_db.execute.return_value = mock_result

        # Mock services - methods must be AsyncMock
        mock_stt = MockSTT.return_value
        mock_stt.transcribe = AsyncMock(return_value={"text": "Hello world", "segments": []})

        mock_llm = MockLLM.return_value
        mock_llm.translate = AsyncMock(return_value="你好世界")
        mock_llm.generate_summary = AsyncMock(return_value={"summary": "Summary", "key_points": []})

        # Patch where read_audio_data is defined
        with patch("app.utils.large_object.read_audio_data", return_value=b"audio"):
            # Fix: pass ctx argument and string id
            result = await process_uploaded_audio_task({}, rec_id)

        assert result["status"] == "completed"
        assert mock_rec.status == "completed"

        MockSTT.assert_called()
        MockLLM.assert_called()
        mock_stt.transcribe.assert_called()
        mock_llm.translate.assert_called()


@pytest.mark.asyncio
async def test_process_uploaded_audio_task_failure():
    """验证处理失败状态更新"""
    rec_id = str(uuid4())

    with (
        patch("app.workers.tasks.async_session") as mock_session_ctx,
        patch("app.workers.tasks.STTService") as MockSTT,
    ):
        mock_db = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_db

        mock_rec = MagicMock()
        mock_rec.id = uuid4()

        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_rec

        mock_stt = MockSTT.return_value
        # Simulate transcribe failure
        mock_stt.transcribe = AsyncMock(side_effect=Exception("Service Init Failed"))

        with patch("app.utils.large_object.read_audio_data", return_value=b"audio"):
            # Fix: pass ctx argument
            result = await process_uploaded_audio_task({}, rec_id)

        assert result["status"] == "failed"
