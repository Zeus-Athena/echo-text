"""
Share API Routes
分享链接接口
"""

import secrets
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from passlib.hash import bcrypt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.recording import Recording, ShareLink
from app.models.user import User

router = APIRouter(prefix="/share", tags=["Share"])


# Request/Response Models
class CreateShareRequest(BaseModel):
    recording_id: UUID
    expires_in_hours: int | None = 168  # Default 7 days
    max_views: int | None = None
    include_audio: bool = True
    include_translation: bool = True
    include_summary: bool = True
    password: str | None = None


class ShareLinkResponse(BaseModel):
    id: UUID
    token: str
    share_url: str
    expires_at: datetime | None
    max_views: int | None
    view_count: int
    include_audio: bool
    include_translation: bool
    include_summary: bool
    has_password: bool
    created_at: datetime


class SharedRecordingResponse(BaseModel):
    title: str
    duration_seconds: int
    source_lang: str
    target_lang: str
    transcript: str | None
    transcript_segments: list | None
    translation: str | None
    translation_segments: list | None
    summary: str | None
    key_points: list | None
    action_items: list | None
    chapters: list | None
    has_audio: bool
    created_at: datetime


@router.post("/", response_model=ShareLinkResponse)
async def create_share_link(
    request_body: CreateShareRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建分享链接"""
    # Verify recording ownership
    result = await db.execute(
        select(Recording).where(
            Recording.id == request_body.recording_id, Recording.user_id == current_user.id
        )
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="录音不存在")

    # Generate unique token
    token = secrets.token_urlsafe(32)

    # Calculate expiration
    expires_at = None
    if request_body.expires_in_hours:
        expires_at = datetime.utcnow() + timedelta(hours=request_body.expires_in_hours)

    # Hash password if provided
    password_hash = None
    if request_body.password:
        password_hash = bcrypt.hash(request_body.password)

    # Create share link
    share_link = ShareLink(
        recording_id=request_body.recording_id,
        token=token,
        expires_at=expires_at,
        max_views=request_body.max_views,
        include_audio=request_body.include_audio,
        include_translation=request_body.include_translation,
        include_summary=request_body.include_summary,
        password_hash=password_hash,
        created_by=current_user.id,
    )

    db.add(share_link)
    await db.commit()
    await db.refresh(share_link)

    # Build share_url from request headers (for reverse proxy support)
    host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host") or "localhost"
    scheme = request.headers.get("X-Forwarded-Proto", "https" if "443" in host else "http")
    base_url = f"{scheme}://{host}"

    return ShareLinkResponse(
        id=share_link.id,
        token=share_link.token,
        share_url=f"{base_url}/shared/{share_link.token}",
        expires_at=share_link.expires_at,
        max_views=share_link.max_views,
        view_count=share_link.view_count,
        include_audio=share_link.include_audio,
        include_translation=share_link.include_translation,
        include_summary=share_link.include_summary,
        has_password=password_hash is not None,
        created_at=share_link.created_at,
    )


@router.get("/recording/{recording_id}", response_model=list[ShareLinkResponse])
async def get_recording_share_links(
    recording_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取录音的所有分享链接"""
    # Verify recording ownership
    result = await db.execute(
        select(Recording).where(Recording.id == recording_id, Recording.user_id == current_user.id)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="录音不存在")

    # Get share links
    result = await db.execute(select(ShareLink).where(ShareLink.recording_id == recording_id))
    share_links = result.scalars().all()

    # Build base_url from request headers (for reverse proxy support)
    host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host") or "localhost"
    scheme = request.headers.get("X-Forwarded-Proto", "https" if "443" in host else "http")
    base_url = f"{scheme}://{host}"

    return [
        ShareLinkResponse(
            id=sl.id,
            token=sl.token,
            share_url=f"{base_url}/shared/{sl.token}",
            expires_at=sl.expires_at,
            max_views=sl.max_views,
            view_count=sl.view_count,
            include_audio=sl.include_audio,
            include_translation=sl.include_translation,
            include_summary=sl.include_summary,
            has_password=sl.password_hash is not None,
            created_at=sl.created_at,
        )
        for sl in share_links
    ]


@router.delete("/{link_id}")
async def revoke_share_link(
    link_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """撤销分享链接"""
    result = await db.execute(
        select(ShareLink).where(ShareLink.id == link_id, ShareLink.created_by == current_user.id)
    )
    share_link = result.scalar_one_or_none()

    if not share_link:
        raise HTTPException(status_code=404, detail="分享链接不存在")

    await db.delete(share_link)
    await db.commit()

    return {"message": "分享链接已撤销"}


# Public endpoint - no authentication required
@router.get("/access/{token}", response_model=SharedRecordingResponse)
async def access_shared_recording(
    token: str, password: str | None = Query(None), db: AsyncSession = Depends(get_db)
):
    """访问分享的录音（无需登录）"""
    result = await db.execute(
        select(ShareLink)
        .where(ShareLink.token == token)
        .options(
            selectinload(ShareLink.recording).selectinload(Recording.transcript),
            selectinload(ShareLink.recording).selectinload(Recording.translation),
            selectinload(ShareLink.recording).selectinload(Recording.ai_summary),
        )
    )
    share_link = result.scalar_one_or_none()

    if not share_link:
        raise HTTPException(status_code=404, detail="分享链接不存在或已过期")

    # Check validity
    if not share_link.is_valid():
        raise HTTPException(status_code=410, detail="分享链接已过期或已达到最大访问次数")

    # Check password
    if share_link.password_hash:
        if not password:
            raise HTTPException(status_code=401, detail="需要密码才能访问")
        if not bcrypt.verify(password, share_link.password_hash):
            raise HTTPException(status_code=401, detail="密码错误")

    # Increment view count
    share_link.view_count += 1
    await db.commit()

    recording = share_link.recording

    # Normalize first segment timestamp
    transcript_segments = recording.transcript.segments if recording.transcript else None
    if transcript_segments and len(transcript_segments) > 0:
        # Create a shallow copy of the list to avoid side effects if strictly needed,
        # but here we just want the response to have 0.0
        transcript_segments[0]["start"] = 0.0

    # Build response based on share link settings
    response = SharedRecordingResponse(
        title=recording.title,
        duration_seconds=recording.duration_seconds,
        source_lang=recording.source_lang,
        target_lang=recording.target_lang,
        transcript=recording.transcript.full_text if recording.transcript else None,
        transcript_segments=transcript_segments,
        translation=recording.translation.full_text
        if share_link.include_translation and recording.translation
        else None,
        translation_segments=recording.translation.segments
        if share_link.include_translation and recording.translation
        else None,
        summary=recording.ai_summary.summary
        if share_link.include_summary and recording.ai_summary
        else None,
        key_points=recording.ai_summary.key_points
        if share_link.include_summary and recording.ai_summary
        else None,
        action_items=recording.ai_summary.action_items
        if share_link.include_summary and recording.ai_summary
        else None,
        chapters=recording.ai_summary.chapters
        if share_link.include_summary and recording.ai_summary
        else None,
        has_audio=share_link.include_audio
        and (recording.audio_oid is not None or recording.audio_blob_id is not None),
        created_at=recording.created_at,
    )

    return response


@router.get("/access/{token}/audio")
async def access_shared_audio(
    token: str, password: str | None = Query(None), db: AsyncSession = Depends(get_db)
):
    """获取分享录音的音频"""
    from fastapi.responses import StreamingResponse

    result = await db.execute(
        select(ShareLink).where(ShareLink.token == token).options(selectinload(ShareLink.recording))
    )
    share_link = result.scalar_one_or_none()

    if not share_link:
        raise HTTPException(status_code=404, detail="分享链接不存在或已过期")

    if not share_link.is_valid():
        raise HTTPException(status_code=410, detail="分享链接已过期")

    if not share_link.include_audio:
        raise HTTPException(status_code=403, detail="此分享链接不包含音频访问权限")

    # Check password
    if share_link.password_hash:
        if not password:
            raise HTTPException(status_code=401, detail="需要密码才能访问")
        if not bcrypt.verify(password, share_link.password_hash):
            raise HTTPException(status_code=401, detail="密码错误")

    recording = share_link.recording

    # Determine content type
    content_type = (
        "audio/ogg"
        if recording.audio_format == "opus"
        else f"audio/{recording.audio_format or 'webm'}"
    )

    from app.utils.large_object import get_audio_size, stream_audio_chunks

    # Get total size for Content-Length header
    total_size = recording.audio_size or await get_audio_size(
        db, oid=recording.audio_oid, blob_id=recording.audio_blob_id
    )

    return StreamingResponse(
        stream_audio_chunks(db, oid=recording.audio_oid, blob_id=recording.audio_blob_id),
        media_type=content_type,
        headers={"Content-Length": str(total_size), "Accept-Ranges": "bytes"},
    )
