"""
ARQ 后台任务测试
Test ARQ background tasks
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def create_mock_session(initial_result=None):
    """Create a properly mocked async session context manager"""
    mock_db = MagicMock()

    # Mock execute to return a proper result object
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = initial_result

    # Make execute return AsyncMock that resolves to mock_result
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    @asynccontextmanager
    async def session_cm():
        yield mock_db

    return session_cm, mock_db


@pytest.mark.asyncio
async def test_transcribe_audio_task_success():
    """验证：转录任务成功执行"""
    from app.workers.tasks import transcribe_audio_task

    mock_ctx = {}
    recording_id = str(uuid4())

    session_cm, mock_db = create_mock_session(initial_result=None)

    with patch("app.workers.tasks.async_session", session_cm):
        with patch("app.workers.tasks.STTService") as mock_stt_class:
            mock_stt = AsyncMock()
            mock_stt.transcribe.return_value = {
                "text": "Hello world",
                "segments": [{"text": "Hello world", "start": 0, "end": 1}],
            }
            mock_stt_class.return_value = mock_stt

            result = await transcribe_audio_task(
                mock_ctx, recording_id=recording_id, audio_data=b"test audio", source_lang="en"
            )

            assert result["status"] == "completed"
            assert result["text"] == "Hello world"
            assert result["recording_id"] == recording_id


@pytest.mark.asyncio
async def test_transcribe_audio_task_empty_result():
    """验证：转录返回空结果时正确处理"""
    from app.workers.tasks import transcribe_audio_task

    mock_ctx = {}
    recording_id = str(uuid4())

    session_cm, mock_db = create_mock_session()

    with patch("app.workers.tasks.async_session", session_cm):
        with patch("app.workers.tasks.STTService") as mock_stt_class:
            mock_stt = AsyncMock()
            mock_stt.transcribe.return_value = {"text": ""}
            mock_stt_class.return_value = mock_stt

            result = await transcribe_audio_task(
                mock_ctx, recording_id=recording_id, audio_data=b"test audio", source_lang="en"
            )

            assert result["status"] == "completed"
            assert result["text"] == ""


@pytest.mark.asyncio
async def test_generate_summary_task_success():
    """验证：摘要生成任务成功执行"""
    from app.workers.tasks import generate_summary_task

    mock_ctx = {}
    recording_id = str(uuid4())

    # Create mock recording
    mock_recording = MagicMock()
    mock_recording.ai_summary = ""
    mock_recording.key_points = []
    mock_recording.action_items = []
    mock_recording.auto_tags = []
    mock_recording.chapters = []

    session_cm, mock_db = create_mock_session(initial_result=mock_recording)

    with patch("app.workers.tasks.async_session", session_cm):
        with patch("app.workers.tasks.LLMService") as mock_llm_class:
            mock_llm = AsyncMock()
            mock_llm.generate_summary.return_value = {
                "summary": "This is a test summary",
                "key_points": ["Point 1", "Point 2"],
                "action_items": [],
                "auto_tags": ["test"],
                "chapters": [],
            }
            mock_llm_class.return_value = mock_llm

            result = await generate_summary_task(
                mock_ctx,
                recording_id=recording_id,
                transcript="Hello world this is a test",
                target_lang="zh",
            )

            assert result["status"] == "completed"
            assert "summary" in result


@pytest.mark.asyncio
async def test_translate_transcript_task_success():
    """验证：翻译任务成功执行"""
    from app.workers.tasks import translate_transcript_task

    mock_ctx = {}
    recording_id = str(uuid4())

    session_cm, mock_db = create_mock_session(initial_result=None)

    with patch("app.workers.tasks.async_session", session_cm):
        with patch("app.workers.tasks.LLMService") as mock_llm_class:
            mock_llm = AsyncMock()
            mock_llm.translate.return_value = "你好世界"
            mock_llm_class.return_value = mock_llm

            result = await translate_transcript_task(
                mock_ctx,
                recording_id=recording_id,
                transcript="Hello world",
                source_lang="en",
                target_lang="zh",
            )

            assert result["status"] == "completed"
            assert result["translated_text"] == "你好世界"


@pytest.mark.asyncio
async def test_task_handles_exception():
    """验证：任务异常时返回失败状态"""
    from app.workers.tasks import transcribe_audio_task

    mock_ctx = {}
    recording_id = str(uuid4())

    @asynccontextmanager
    async def failing_session():
        raise Exception("Database error")
        yield  # noqa: unreachable

    with patch("app.workers.tasks.async_session", failing_session):
        result = await transcribe_audio_task(
            mock_ctx, recording_id=recording_id, audio_data=b"test audio", source_lang="en"
        )

        assert result["status"] == "failed"
        assert "error" in result
