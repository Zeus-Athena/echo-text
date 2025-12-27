"""
Export Service V2 Tests
Test Markdown and SRT export functionality with correct initialization.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.services.export_service import ExportOptions, ExportService


@pytest.fixture
def mock_recording_for_export():
    rec = MagicMock()
    rec.title = "Export Test"
    rec.duration_seconds = 125
    rec.source_lang = "en"
    rec.target_lang = "zh"
    rec.created_at = datetime(2023, 1, 1, 12, 0, 0)

    # 嵌套 Mock
    rec.transcript = MagicMock()
    rec.transcript.full_text = "Full transcript text."
    rec.transcript.segments = [
        {"start": 0.0, "end": 2.0, "text": "Hello world.", "speaker": "A"},
        {"start": 3.0, "end": 5.0, "text": "Test.", "speaker": "B"},
    ]

    rec.translation = MagicMock()
    rec.translation.full_text = "Full translation text."
    rec.translation.segments = [
        {"start": 0.0, "end": 2.0, "text": "你好世界。"},
        {"start": 3.0, "end": 5.0, "text": "测试。"},
    ]

    rec.ai_summary = MagicMock()
    rec.ai_summary.summary = "A detailed summary."
    rec.ai_summary.key_points = ["Point 1", "Point 2"]
    rec.ai_summary.action_items = ["Item 1"]

    return rec


@pytest.mark.asyncio
async def test_export_markdown_v2(mock_recording_for_export):
    # 正确初始化：传入 recording
    service = ExportService(mock_recording_for_export)

    options = ExportOptions(include_translation=True, include_summary=True)
    content = await service.export_markdown(options)

    assert "# Export Test" in content
    assert "你好世界" in content
    assert "A detailed summary" in content


@pytest.mark.asyncio
async def test_export_srt_v2(mock_recording_for_export):
    service = ExportService(mock_recording_for_export)

    content = await service.export_srt(use_translation=False)
    assert "00:00:00,000 --> 00:00:02,000" in content
    assert "Hello world." in content

    content_zh = await service.export_srt(use_translation=True)
    assert "你好世界。" in content_zh


def test_duration_formatting():
    # 虽然是实例方法，但逻辑不依赖于实例状态
    service = ExportService(MagicMock())
    assert service._format_duration(125) == "2:05"
    assert service._format_duration(3665) == "1:01:05"
