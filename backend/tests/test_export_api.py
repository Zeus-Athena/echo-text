"""
Export API Tests
测试导出 API 端点
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
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
    return db


@pytest.fixture
def mock_recording():
    """创建模拟 Recording 对象"""
    recording = MagicMock()
    recording.id = uuid4()
    recording.title = "Test Recording"
    recording.duration_seconds = 300
    recording.created_at = datetime(2024, 1, 15, 10, 30, 0)
    recording.source_lang = "en"
    recording.target_lang = "zh"

    # Mock transcript
    recording.transcript = MagicMock()
    recording.transcript.full_text = "Hello world. This is a test."
    recording.transcript.segments = [
        {"text": "Hello world.", "start": 0.0, "end": 2.0},
        {"text": "This is a test.", "start": 2.5, "end": 5.0},
    ]

    # Mock translation
    recording.translation = MagicMock()
    recording.translation.full_text = "你好世界。这是一个测试。"
    recording.translation.segments = [
        {"text": "你好世界。", "start": 0.0, "end": 2.0},
        {"text": "这是一个测试。", "start": 2.5, "end": 5.0},
    ]

    # Mock summary
    recording.ai_summary = None

    return recording


class TestExportRecording:
    """测试导出录音端点"""

    @pytest.mark.asyncio
    async def test_export_invalid_format(self, mock_user, mock_db):
        """测试无效导出格式"""
        from fastapi import HTTPException

        from app.api.v1.export import export_recording

        with pytest.raises(HTTPException) as exc:
            await export_recording(
                recording_id=uuid4(),
                format="invalid",
                current_user=mock_user,
                db=mock_db,
            )

        assert exc.value.status_code == 400
        assert "不支持的导出格式" in exc.value.detail

    @pytest.mark.asyncio
    async def test_export_recording_not_found(self, mock_user, mock_db):
        """测试录音不存在"""
        from fastapi import HTTPException

        from app.api.v1.export import export_recording

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await export_recording(
                recording_id=uuid4(),
                format="markdown",
                current_user=mock_user,
                db=mock_db,
            )

        assert exc.value.status_code == 404
        assert "录音不存在" in exc.value.detail

    @pytest.mark.asyncio
    async def test_export_markdown_success(self, mock_user, mock_db, mock_recording):
        """测试 Markdown 导出成功"""
        from app.api.v1.export import export_recording

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_recording
        mock_db.execute.return_value = mock_result

        response = await export_recording(
            recording_id=mock_recording.id,
            format="markdown",
            current_user=mock_user,
            db=mock_db,
        )

        assert response.status_code == 200
        assert response.media_type == "text/markdown; charset=utf-8"
        # Check Content-Disposition header
        assert "attachment" in response.headers["Content-Disposition"]
        assert ".md" in response.headers["Content-Disposition"]

    @pytest.mark.asyncio
    async def test_export_srt_success(self, mock_user, mock_db, mock_recording):
        """测试 SRT 导出成功"""
        from app.api.v1.export import export_recording

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_recording
        mock_db.execute.return_value = mock_result

        response = await export_recording(
            recording_id=mock_recording.id,
            format="srt",
            current_user=mock_user,
            db=mock_db,
        )

        assert response.status_code == 200
        assert "text/plain" in response.media_type
        assert ".srt" in response.headers["Content-Disposition"]

    @pytest.mark.asyncio
    async def test_export_pdf_success(self, mock_user, mock_db, mock_recording):
        """测试 PDF 导出成功"""
        from app.api.v1.export import export_recording

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_recording
        mock_db.execute.return_value = mock_result

        with patch(
            "app.services.export_service.ExportService.export_pdf", new_callable=AsyncMock
        ) as mock_pdf:
            mock_pdf.return_value = b"%PDF-1.4 fake pdf content"
            response = await export_recording(
                recording_id=mock_recording.id,
                format="pdf",
                current_user=mock_user,
                db=mock_db,
            )

        assert response.status_code == 200
        assert response.media_type == "application/pdf"
        assert ".pdf" in response.headers["Content-Disposition"]

    @pytest.mark.asyncio
    async def test_export_docx_success(self, mock_user, mock_db, mock_recording):
        """测试 DOCX 导出成功"""
        from app.api.v1.export import export_recording

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_recording
        mock_db.execute.return_value = mock_result

        with patch(
            "app.services.export_service.ExportService.export_docx", new_callable=AsyncMock
        ) as mock_docx:
            mock_docx.return_value = b"PK fake docx content"
            response = await export_recording(
                recording_id=mock_recording.id,
                format="docx",
                current_user=mock_user,
                db=mock_db,
            )

        assert response.status_code == 200
        assert "openxmlformats" in response.media_type
        assert ".docx" in response.headers["Content-Disposition"]

    @pytest.mark.asyncio
    async def test_export_with_unicode_title(self, mock_user, mock_db, mock_recording):
        """测试包含 Unicode 字符的标题导出"""
        from app.api.v1.export import export_recording

        mock_recording.title = "会议记录 - 2024年1月"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_recording
        mock_db.execute.return_value = mock_result

        response = await export_recording(
            recording_id=mock_recording.id,
            format="markdown",
            current_user=mock_user,
            db=mock_db,
        )

        assert response.status_code == 200
        # Check UTF-8 filename is properly encoded
        assert "filename*=UTF-8''" in response.headers["Content-Disposition"]

    @pytest.mark.asyncio
    async def test_export_options_passed_correctly(self, mock_user, mock_db, mock_recording):
        """测试导出选项正确传递"""
        from app.api.v1.export import export_recording

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_recording
        mock_db.execute.return_value = mock_result

        response = await export_recording(
            recording_id=mock_recording.id,
            format="markdown",
            include_transcript=True,
            include_translation=False,
            include_summary=False,
            include_timestamps=True,
            current_user=mock_user,
            db=mock_db,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_export_srt_with_translation(self, mock_user, mock_db, mock_recording):
        """测试 SRT 导出使用翻译内容"""
        from app.api.v1.export import export_recording

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_recording
        mock_db.execute.return_value = mock_result

        response = await export_recording(
            recording_id=mock_recording.id,
            format="srt",
            use_translation=True,
            current_user=mock_user,
            db=mock_db,
        )

        assert response.status_code == 200
        # Body should contain Chinese translation
        body = response.body.decode("utf-8")
        assert "你好世界" in body
