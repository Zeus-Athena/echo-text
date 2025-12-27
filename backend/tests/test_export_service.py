"""
Export Service 测试
Test document export functionality (Markdown, SRT, PDF, DOCX)
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest


def create_mock_recording():
    """创建模拟 Recording 对象"""
    recording = MagicMock()
    recording.title = "Test Recording"
    recording.duration_seconds = 300  # 5 minutes
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


@pytest.mark.asyncio
async def test_export_markdown():
    """验证：Markdown 导出"""
    from app.services.export_service import ExportService

    recording = create_mock_recording()
    service = ExportService(recording)

    result = await service.export_markdown()

    assert isinstance(result, str)
    assert "Test Recording" in result
    assert "Hello world" in result
    assert "你好世界" in result


@pytest.mark.asyncio
async def test_export_markdown_no_translation():
    """验证：无翻译时的 Markdown 导出"""
    from app.services.export_service import ExportOptions, ExportService

    recording = create_mock_recording()
    recording.translation = None
    service = ExportService(recording)

    options = ExportOptions(include_translation=False)
    result = await service.export_markdown(options)

    assert "Hello world" in result


@pytest.mark.asyncio
async def test_export_srt():
    """验证：SRT 字幕导出"""
    from app.services.export_service import ExportService

    recording = create_mock_recording()
    service = ExportService(recording)

    result = await service.export_srt(use_translation=False)

    assert isinstance(result, str)
    assert "1\n" in result
    assert "Hello world" in result
    assert "-->" in result


@pytest.mark.asyncio
async def test_export_srt_translation():
    """验证：SRT 翻译字幕导出"""
    from app.services.export_service import ExportService

    recording = create_mock_recording()
    service = ExportService(recording)

    result = await service.export_srt(use_translation=True)

    assert "你好世界" in result


def test_format_duration():
    """验证：时长格式化"""
    from app.services.export_service import ExportService

    recording = create_mock_recording()
    service = ExportService(recording)

    # 实际格式: M:SS 或 H:MM:SS
    assert service._format_duration(0) == "0:00"
    assert service._format_duration(65) == "1:05"
    assert service._format_duration(3661) == "1:01:01"


def test_format_timestamp():
    """验证：时间戳格式化 MM:SS"""
    from app.services.export_service import ExportService

    recording = create_mock_recording()
    service = ExportService(recording)

    assert service._format_timestamp(0) == "00:00"
    assert service._format_timestamp(65.5) == "01:05"
    assert service._format_timestamp(3661) == "61:01"


def test_format_srt_time():
    """验证：SRT 时间戳格式化 HH:MM:SS,mmm"""
    from app.services.export_service import ExportService

    recording = create_mock_recording()
    service = ExportService(recording)

    assert service._format_srt_time(0) == "00:00:00,000"
    assert service._format_srt_time(65.5) == "00:01:05,500"
    assert service._format_srt_time(3661.123) == "01:01:01,123"


def test_export_options_defaults():
    """验证：ExportOptions 默认值"""
    from app.services.export_service import ExportOptions

    options = ExportOptions()

    assert options.include_transcript is True
    assert options.include_translation is True
    assert options.include_summary is True
    assert options.include_timestamps is True
