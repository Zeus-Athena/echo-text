"""
Export API Routes
导出接口
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.recording import Recording
from app.models.user import User
from app.services.export_service import ExportOptions, ExportService

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/{recording_id}/{format}")
async def export_recording(
    recording_id: UUID,
    format: str,  # pdf | markdown | docx | srt
    include_transcript: bool = Query(True, description="包含转录内容"),
    include_translation: bool = Query(True, description="包含翻译内容"),
    include_summary: bool = Query(True, description="包含AI总结"),
    include_timestamps: bool = Query(True, description="包含时间戳"),
    use_translation: bool = Query(False, description="SRT导出使用翻译内容"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    导出录音内容为指定格式

    支持格式:
    - markdown: Markdown 文本
    - pdf: PDF 文档
    - docx: Word 文档
    - srt: SRT 字幕文件
    """
    # 验证格式
    valid_formats = {"markdown", "pdf", "docx", "srt"}
    if format not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的导出格式: {format}。支持的格式: {', '.join(valid_formats)}",
        )

    # 获取录音详情
    result = await db.execute(
        select(Recording)
        .where(Recording.id == recording_id, Recording.user_id == current_user.id)
        .options(
            selectinload(Recording.transcript),
            selectinload(Recording.translation),
            selectinload(Recording.ai_summary),
        )
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="录音不存在")

    # 创建导出服务
    export_service = ExportService(recording)
    options = ExportOptions(
        include_transcript=include_transcript,
        include_translation=include_translation,
        include_summary=include_summary,
        include_timestamps=include_timestamps,
    )

    # Create timestamp string from recording creation time (e.g., 20231219_2340)
    # Using UTC for consistency, but often local time is preferred for filenames.
    # Let's use the recording's created_at.
    timestamp = recording.created_at.strftime("%Y%m%d_%H%M")

    # Secure filename: Title + Timestamp
    # For the standard filename parameter, only use ASCII characters (for older browsers/HTTP headers)
    # For filename*, use the full UTF-8 encoded title
    from urllib.parse import quote

    # ASCII-safe filename for fallback (strip non-ASCII)
    ascii_safe_title = "".join(
        c for c in recording.title if c.isascii() and (c.isalnum() or c in " -_")
    ).strip()
    ascii_safe_title = ascii_safe_title[:50] or "recording"
    ascii_filename_no_ext = f"{ascii_safe_title}_{timestamp}"

    # Full title with proper characters for UTF-8 encoding (filename* parameter)
    utf8_safe_title = "".join(c for c in recording.title if c.isalnum() or c in " -_").strip()
    utf8_safe_title = utf8_safe_title[:50] or "recording"
    utf8_filename_no_ext = f"{utf8_safe_title}_{timestamp}"
    encoded_title = quote(utf8_filename_no_ext)

    def get_headers(ext):
        # We provide both standard filename for older browsers and filename* for modern ones
        # The filename parameter uses ASCII-only for HTTP header compatibility
        # The filename* parameter uses UTF-8 encoding for proper Unicode support
        return {
            "Content-Disposition": f"attachment; filename=\"{ascii_filename_no_ext}.{ext}\"; filename*=UTF-8''{encoded_title}.{ext}"
        }

    try:
        if format == "markdown":
            content = await export_service.export_markdown(options)
            return Response(
                content=content,
                media_type="text/markdown; charset=utf-8",
                headers=get_headers("md"),
            )

        elif format == "pdf":
            content = await export_service.export_pdf(options)
            return Response(
                content=content, media_type="application/pdf", headers=get_headers("pdf")
            )

        elif format == "docx":
            content = await export_service.export_docx(options)
            return Response(
                content=content,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers=get_headers("docx"),
            )

        elif format == "srt":
            content = await export_service.export_srt(use_translation=use_translation)
            return Response(
                content=content, media_type="text/plain; charset=utf-8", headers=get_headers("srt")
            )

    except ImportError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")
