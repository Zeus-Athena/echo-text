"""
Recording API Routes
录音相关接口
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from loguru import logger
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_effective_config
from app.core.database import get_db
from app.models.recording import AISummary, Folder, Recording, Tag, Transcript, Translation
from app.models.user import User
from app.schemas.recording import (
    BatchDeleteRequest,
    BatchMoveRequest,
    FolderCreate,
    FolderListResponse,
    FolderResponse,
    RecordingCreate,
    RecordingDetail,
    RecordingListItem,
    RecordingUpdate,
    TagCreate,
    TagResponse,
    TranscriptUpdate,
    TranslationUpdate,
)

router = APIRouter(prefix="/recordings", tags=["Recordings"])


# ========== Folders ==========


@router.get("/folders", response_model=FolderListResponse)
async def list_folders(
    source_type: str | None = "realtime",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all folders for current user with recording counts (filtered by source_type)"""
    # 1. Query folders and count recordings for each
    # Filter folders by source_type
    query = (
        select(Folder, func.count(Recording.id).label("recording_count"))
        .outerjoin(Recording, Folder.id == Recording.folder_id)
        .where(Folder.user_id == current_user.id, Folder.source_type == source_type)
        .group_by(Folder.id)
    )
    result = await db.execute(query)

    folders_with_counts = []
    # result is an iterator of rows, each row is a tuple (Folder, count)
    for folder, count in result:
        folder.recording_count = count
        folders_with_counts.append(folder)

    # 2. Query total count for "All Recordings" (filtered by source_type)
    total_query = select(func.count(Recording.id)).where(
        Recording.user_id == current_user.id, Recording.source_type == source_type
    )
    total_result = await db.execute(total_query)
    total_count = total_result.scalar() or 0

    # 3. Query count for "Uncategorized" (Default Folder) (filtered by source_type)
    uncategorized_query = select(func.count(Recording.id)).where(
        Recording.user_id == current_user.id,
        Recording.folder_id.is_(None),
        Recording.source_type == source_type,
    )
    uncategorized_result = await db.execute(uncategorized_query)
    uncategorized_count = uncategorized_result.scalar() or 0

    return {
        "folders": folders_with_counts,
        "total_recordings": total_count,
        "uncategorized_count": uncategorized_count,
    }


@router.post("/folders", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_data: FolderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new folder"""
    folder = Folder(
        user_id=current_user.id,
        name=folder_data.name,
        parent_id=folder_data.parent_id,
        source_type=folder_data.source_type,
    )
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder


@router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a folder"""
    result = await db.execute(
        select(Folder).where(Folder.id == folder_id, Folder.user_id == current_user.id)
    )
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    await db.delete(folder)
    await db.commit()
    return {"message": "Folder deleted"}


# ========== Tags ==========


@router.get("/tags", response_model=list[TagResponse])
async def list_tags(db: AsyncSession = Depends(get_db)):
    """List all tags"""
    result = await db.execute(select(Tag))
    tags = result.scalars().all()
    return tags


@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_data: TagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new tag"""
    # Check if tag already exists
    result = await db.execute(select(Tag).where(Tag.name == tag_data.name))
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    tag = Tag(name=tag_data.name, color=tag_data.color)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


# ========== Recordings ==========


@router.get("/", response_model=list[RecordingListItem])
async def list_recordings(
    folder_id: UUID | None = None,
    search: str | None = None,
    tag: str | None = None,
    source_type: str | None = None,  # Filter by source: 'realtime' or 'upload'
    uncategorized: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List recordings with optional filters"""
    query = select(Recording).where(Recording.user_id == current_user.id)

    if folder_id:
        query = query.where(Recording.folder_id == folder_id)
    elif uncategorized:
        query = query.where(Recording.folder_id.is_(None))

    if search:
        query = query.where(Recording.title.ilike(f"%{search}%"))

    if source_type:
        query = query.where(Recording.source_type == source_type)

    query = query.options(selectinload(Recording.tags), selectinload(Recording.ai_summary))
    query = query.order_by(Recording.created_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    recordings = result.scalars().all()

    return [
        RecordingListItem(
            id=r.id,
            title=r.title,
            duration_seconds=r.duration_seconds,
            source_lang=r.source_lang,
            target_lang=r.target_lang,
            status=r.status,
            source_type=r.source_type,
            has_summary=r.ai_summary is not None,
            tags=[TagResponse(id=t.id, name=t.name, color=t.color) for t in r.tags],
            created_at=r.created_at,
        )
        for r in recordings
    ]


@router.post("/", response_model=RecordingDetail, status_code=status.HTTP_201_CREATED)
async def create_recording(
    recording_data: RecordingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new recording entry"""
    recording = Recording(
        user_id=current_user.id,
        title=recording_data.title,
        source_lang=recording_data.source_lang,
        target_lang=recording_data.target_lang,
        folder_id=recording_data.folder_id,
        status="processing",
    )
    db.add(recording)
    await db.commit()
    await db.refresh(recording)

    return RecordingDetail(
        id=recording.id,
        title=recording.title,
        s3_key=recording.s3_key,
        audio_url=None,
        duration_seconds=recording.duration_seconds,
        source_lang=recording.source_lang,
        target_lang=recording.target_lang,
        status=recording.status,
        source_type=recording.source_type,
        folder_id=recording.folder_id,
        tags=[],
        transcript=None,
        translation=None,
        ai_summary=None,
        created_at=recording.created_at,
        updated_at=recording.updated_at,
    )


@router.get("/{recording_id}", response_model=RecordingDetail)
async def get_recording(
    recording_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recording details"""
    result = await db.execute(
        select(Recording)
        .where(Recording.id == recording_id, Recording.user_id == current_user.id)
        .options(
            selectinload(Recording.tags),
            selectinload(Recording.transcript),
            selectinload(Recording.translation),
            selectinload(Recording.ai_summary),
        )
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Normalize first segment timestamp to 0.0 for better UI experience
    if recording.transcript and recording.transcript.segments:
        if len(recording.transcript.segments) > 0:
            # Modify in-memory object (safe as we don't commit in GET)
            # This ensures the first card always starts at the beginning
            recording.transcript.segments[0]["start"] = 0.0

    return recording


@router.put("/{recording_id}", response_model=RecordingDetail)
async def update_recording(
    recording_id: UUID,
    recording_data: RecordingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update recording"""
    result = await db.execute(
        select(Recording)
        .where(Recording.id == recording_id, Recording.user_id == current_user.id)
        .options(selectinload(Recording.tags))
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    if recording_data.title:
        recording.title = recording_data.title
    if recording_data.folder_id is not None:
        recording.folder_id = recording_data.folder_id
    if recording_data.tag_ids is not None:
        # Update tags
        tag_result = await db.execute(select(Tag).where(Tag.id.in_(recording_data.tag_ids)))
        recording.tags = list(tag_result.scalars().all())

    await db.commit()
    await db.refresh(recording)

    return await get_recording(recording_id, current_user, db)


@router.delete("/{recording_id}")
async def delete_recording(
    recording_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a recording and its audio data"""
    from app.utils.large_object import delete_audio_data

    result = await db.execute(
        select(Recording).where(Recording.id == recording_id, Recording.user_id == current_user.id)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Delete audio data from database
    if recording.audio_oid or recording.audio_blob_id:
        await delete_audio_data(db, oid=recording.audio_oid, blob_id=recording.audio_blob_id)

    await db.delete(recording)
    await db.commit()

    logger.info(f"Deleted recording: {recording_id}")
    return {"message": "Recording deleted"}


# ========== Batch Operations ==========


@router.post("/batch/delete")
async def batch_delete_recordings(
    request: BatchDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Batch delete recordings"""
    await db.execute(
        delete(Recording).where(Recording.id.in_(request.ids), Recording.user_id == current_user.id)
    )
    await db.commit()
    return {"message": f"Deleted {len(request.ids)} recordings"}


@router.post("/batch/move")
async def batch_move_recordings(
    request: BatchMoveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Batch move recordings to folder"""
    result = await db.execute(
        select(Recording).where(Recording.id.in_(request.ids), Recording.user_id == current_user.id)
    )
    recordings = result.scalars().all()

    for recording in recordings:
        recording.folder_id = request.folder_id

    await db.commit()
    return {"message": f"Moved {len(recordings)} recordings"}


# ========== Audio Upload & STT ==========


@router.post("/upload", response_model=RecordingDetail, status_code=status.HTTP_201_CREATED)
async def upload_audio(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    source_lang: str = Form("en"),
    target_lang: str = Form("zh"),
    folder_id: UUID | None = Form(None),
    auto_process: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload audio file, compress to Opus, and store in database

    If auto_process=True, triggers background processing (transcribe -> translate -> AI analyze)
    """
    import os
    import tempfile

    from app.utils.audio_utils import compress_to_opus, convert_webm_to_wav, get_audio_duration
    from app.utils.large_object import save_audio_data

    # Read file content
    content = await file.read()

    # Convert WebM to WAV if needed (for duration calculation and conversion)
    if file.filename and file.filename.endswith(".webm"):
        wav_content = convert_webm_to_wav(content)
    else:
        wav_content = content

    # Get duration from WAV
    duration = 0
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_content)
            tmp_path = tmp.name
        duration = get_audio_duration(tmp_path)
        os.unlink(tmp_path)
    except Exception as e:
        logger.warning(f"Could not get audio duration: {e}")

    # Compress to Opus format
    opus_content = compress_to_opus(wav_content, bitrate="48k")
    audio_size = len(opus_content)

    # Store in database using Large Object (PostgreSQL) or BLOB (SQLite)
    audio_oid, audio_blob_id = await save_audio_data(db, opus_content)

    # Create recording
    recording = Recording(
        user_id=current_user.id,
        title=title or file.filename or "录音",
        s3_key=None,  # No longer using file system
        duration_seconds=int(duration),
        source_lang=source_lang,
        target_lang=target_lang,
        folder_id=folder_id,
        audio_oid=audio_oid,
        audio_blob_id=audio_blob_id,
        audio_size=audio_size,
        audio_format="opus",
        source_type="upload",  # Mark as uploaded (not realtime)
        status="processing" if auto_process else "uploaded",
    )
    db.add(recording)
    await db.commit()
    await db.refresh(recording)

    logger.info(
        f"Uploaded recording: {recording.id}, audio_oid={audio_oid}, audio_blob_id={audio_blob_id}, size={audio_size}"
    )

    # Trigger background processing if requested
    if auto_process:
        from arq import create_pool

        from app.workers.settings import REDIS_SETTINGS

        try:
            redis = await create_pool(REDIS_SETTINGS)

            # Get user config ID for the task
            from app.models.user import UserConfig

            config_result = await db.execute(
                select(UserConfig).where(UserConfig.user_id == current_user.id)
            )
            user_config = config_result.scalar_one_or_none()
            user_config_id = str(user_config.user_id) if user_config else None

            await redis.enqueue_job(
                "process_uploaded_audio_task", str(recording.id), user_config_id
            )
            await redis.close()
            logger.info(f"Enqueued processing task for recording {recording.id}")
        except Exception as e:
            logger.error(f"Failed to enqueue processing task: {e}")
            # Don't fail the upload, just log the error

    return RecordingDetail(
        id=recording.id,
        title=recording.title,
        s3_key=recording.s3_key,
        audio_url=f"/api/v1/recordings/{recording.id}/audio",
        audio_format=recording.audio_format,
        audio_size=recording.audio_size,
        duration_seconds=recording.duration_seconds,
        source_lang=recording.source_lang,
        target_lang=recording.target_lang,
        status=recording.status,
        folder_id=recording.folder_id,
        tags=[],
        transcript=None,
        translation=None,
        ai_summary=None,
        created_at=recording.created_at,
        updated_at=recording.updated_at,
    )


@router.get("/{recording_id}/audio")
async def get_audio(
    recording_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get audio file for recording with Range header support"""
    from app.utils.large_object import get_audio_size

    result = await db.execute(
        select(Recording).where(Recording.id == recording_id, Recording.user_id == current_user.id)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    logger.info(
        f"[DEBUG] get_audio called for recording_id={recording_id}, audio_oid={recording.audio_oid}, audio_blob_id={recording.audio_blob_id}, s3_key={recording.s3_key}"
    )

    # Check if audio data exists (either Large Object or BLOB)
    if not recording.audio_oid and not recording.audio_blob_id:
        # Fallback: check s3_key for legacy file-based storage
        import os

        if recording.s3_key and os.path.exists(recording.s3_key):
            from fastapi.responses import FileResponse

            return FileResponse(recording.s3_key, media_type="audio/wav")
        raise HTTPException(status_code=404, detail="Audio not found")

    # Determine content type based on format
    content_type = "audio/ogg" if recording.audio_format == "opus" else "audio/wav"

    try:
        # Get total size
        total_size = recording.audio_size or await get_audio_size(
            db, oid=recording.audio_oid, blob_id=recording.audio_blob_id
        )
        logger.info(
            f"[DEBUG] Starting audio stream for recording {recording_id}, total_size={total_size}"
        )

        # URL encode filename for non-ASCII characters (RFC 5987)
        from urllib.parse import quote

        safe_filename = quote(f"{recording.title}.opus", safe="")

        from fastapi.responses import StreamingResponse

        from app.utils.large_object import stream_audio_chunks

        return StreamingResponse(
            stream_audio_chunks(db, oid=recording.audio_oid, blob_id=recording.audio_blob_id),
            media_type=content_type,
            headers={
                "Content-Length": str(total_size),
                "Accept-Ranges": "bytes",
                "Content-Disposition": f"inline; filename*=UTF-8''{safe_filename}",
            },
        )
    except Exception as e:
        logger.error(f"[ERROR] Failed to read audio for recording {recording_id}: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to read audio: {str(e)}")


@router.post("/{recording_id}/process")
async def process_recording(
    recording_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger background processing for an uploaded recording (transcribe -> translate -> AI analyze)"""
    # Get recording
    result = await db.execute(
        select(Recording).where(Recording.id == recording_id, Recording.user_id == current_user.id)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Check if already processing or completed
    if recording.status in ["processing", "transcribing", "translating", "analyzing"]:
        raise HTTPException(status_code=400, detail="Recording is already being processed")

    if recording.status == "completed":
        raise HTTPException(status_code=400, detail="Recording has already been processed")

    # Update status to processing
    recording.status = "processing"
    await db.commit()

    # Enqueue task
    from arq import create_pool

    from app.workers.settings import REDIS_SETTINGS

    try:
        redis = await create_pool(REDIS_SETTINGS)

        # Get user config ID for the task
        from app.models.user import UserConfig

        config_result = await db.execute(
            select(UserConfig).where(UserConfig.user_id == current_user.id)
        )
        user_config = config_result.scalar_one_or_none()
        user_config_id = str(user_config.user_id) if user_config else None

        await redis.enqueue_job("process_uploaded_audio_task", str(recording_id), user_config_id)
        await redis.close()

        logger.info(f"Enqueued processing task for recording {recording_id}")

        return {"status": "processing", "message": "Processing started"}

    except Exception as e:
        logger.error(f"Failed to enqueue processing task: {e}")
        recording.status = "uploaded"  # Revert status
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to start processing: {str(e)}")


@router.post("/{recording_id}/transcribe")
async def transcribe_recording(
    recording_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Transcribe recording using STT service"""
    from app.services.stt_service import STTService
    from app.utils.large_object import read_audio_data

    # Get recording
    result = await db.execute(
        select(Recording)
        .where(Recording.id == recording_id, Recording.user_id == current_user.id)
        .options(selectinload(Recording.transcript))
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Check for audio data
    if not recording.audio_oid and not recording.audio_blob_id and not recording.s3_key:
        raise HTTPException(status_code=400, detail="No audio file for this recording")

    # Get effective config for STT (admin's config if can_use_admin_key=true)
    user_config = await get_effective_config(current_user, db)

    # Initialize STT service
    stt = STTService(user_config)

    try:
        # Get audio data from database or file
        if recording.audio_oid or recording.audio_blob_id:
            audio_data = await read_audio_data(
                db, oid=recording.audio_oid, blob_id=recording.audio_blob_id
            )
            filename = f"audio.{recording.audio_format}"
        else:
            # Legacy: read from file
            with open(recording.s3_key, "rb") as f:
                audio_data = f.read()
            filename = recording.s3_key.split("/")[-1]

        # Transcribe
        result = await stt.transcribe(audio_data, recording.source_lang, filename)

        # Save transcript
        if recording.transcript:
            recording.transcript.full_text = result["text"]
            recording.transcript.segments = result["segments"]
        else:
            transcript = Transcript(
                recording_id=recording.id, full_text=result["text"], segments=result["segments"]
            )
            db.add(transcript)

        recording.status = "transcribed"
        await db.commit()

        return {
            "success": True,
            "text": result["text"],
            "segments": result["segments"],
            "language": result.get("language", recording.source_lang),
        }

    except Exception as e:
        recording.status = "error"
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.put("/{recording_id}/transcript")
async def update_transcript(
    recording_id: UUID,
    data: TranscriptUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update transcript content (for search/replace save)"""
    logger.info(
        f"[DEBUG] update_transcript called for recording_id={recording_id}, content_length={len(data.full_text) if data.full_text else 0}"
    )

    result = await db.execute(
        select(Recording)
        .where(Recording.id == recording_id, Recording.user_id == current_user.id)
        .options(selectinload(Recording.transcript))
    )
    recording = result.scalar_one_or_none()

    if not recording:
        logger.error(f"[DEBUG] Recording not found: {recording_id}")
        raise HTTPException(status_code=404, detail="Recording not found")

    if recording.transcript:
        logger.info(f"[DEBUG] Updating existing transcript for recording {recording_id}")
        recording.transcript.full_text = data.full_text
        if data.segments is not None:
            recording.transcript.segments = data.segments
    else:
        logger.info(f"[DEBUG] Creating new transcript for recording {recording_id}")
        transcript = Transcript(
            recording_id=recording.id, full_text=data.full_text, segments=data.segments or []
        )
        db.add(transcript)

    await db.commit()
    logger.info(f"[DEBUG] Transcript saved and committed for recording {recording_id}")
    return {"success": True, "message": "Transcript updated"}


@router.put("/{recording_id}/translation")
async def update_translation(
    recording_id: UUID,
    data: TranslationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update translation content (for search/replace save)"""
    result = await db.execute(
        select(Recording)
        .where(Recording.id == recording_id, Recording.user_id == current_user.id)
        .options(selectinload(Recording.translation))
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    if recording.translation:
        recording.translation.full_text = data.full_text
        if data.segments is not None:
            recording.translation.segments = data.segments
    else:
        translation = Translation(
            recording_id=recording.id, full_text=data.full_text, segments=data.segments or []
        )
        db.add(translation)

    await db.commit()
    return {"success": True, "message": "Translation updated"}


@router.post("/{recording_id}/translate")
async def translate_recording(
    recording_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Translate transcript using LLM"""
    from app.services.llm_service import LLMService

    result = await db.execute(
        select(Recording)
        .where(Recording.id == recording_id, Recording.user_id == current_user.id)
        .options(selectinload(Recording.transcript), selectinload(Recording.translation))
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    if not recording.transcript or not recording.transcript.full_text:
        raise HTTPException(status_code=400, detail="No transcript to translate")

    # Get effective config (admin's config if can_use_admin_key=true)
    user_config = await get_effective_config(current_user, db)

    llm = LLMService(user_config)

    try:
        translated = await llm.translate(
            recording.transcript.full_text,
            source_lang=recording.source_lang,
            target_lang=recording.target_lang,
        )

        if recording.translation:
            recording.translation.full_text = translated
        else:
            translation = Translation(recording_id=recording.id, full_text=translated, segments=[])
            db.add(translation)

        recording.status = "translated"
        await db.commit()

        return {"success": True, "translation": translated}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


@router.post("/{recording_id}/summarize")
async def generate_summary(
    recording_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI summary from transcript"""
    from app.services.llm_service import LLMService

    result = await db.execute(
        select(Recording)
        .where(Recording.id == recording_id, Recording.user_id == current_user.id)
        .options(selectinload(Recording.transcript), selectinload(Recording.ai_summary))
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    if not recording.transcript or not recording.transcript.full_text:
        raise HTTPException(status_code=400, detail="No transcript to summarize")

    # Get effective config (admin's config if can_use_admin_key=true)
    user_config = await get_effective_config(current_user, db)

    llm = LLMService(user_config)

    try:
        # Pass segments and duration for chapter generation
        segments = recording.transcript.segments if recording.transcript.segments else []
        summary_data = await llm.generate_summary(
            recording.transcript.full_text,
            target_lang=recording.target_lang,
            segments=segments,
            duration_seconds=recording.duration_seconds,
        )

        # Debug logging
        from loguru import logger

        logger.info(f"[DEBUG] summary_data: {summary_data}")
        logger.info(
            f"[DEBUG] chapters type: {type(summary_data.get('chapters'))}, value: {summary_data.get('chapters')}"
        )

        if recording.ai_summary:
            recording.ai_summary.summary = summary_data["summary"]
            recording.ai_summary.key_points = summary_data["key_points"]
            recording.ai_summary.action_items = summary_data.get("action_items", [])
            recording.ai_summary.auto_tags = summary_data.get("auto_tags", [])
            recording.ai_summary.chapters = summary_data.get("chapters", [])
        else:
            ai_summary = AISummary(
                recording_id=recording.id,
                summary=summary_data["summary"],
                key_points=summary_data["key_points"],
                action_items=summary_data.get("action_items", []),
                auto_tags=summary_data.get("auto_tags", []),
                chapters=summary_data.get("chapters", []),
            )
            db.add(ai_summary)

        await db.commit()

        return {"success": True, **summary_data}

    except Exception as e:
        import traceback

        from loguru import logger

        logger.error(f"[ERROR] Summary generation failed: {e}")
        logger.error(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")
