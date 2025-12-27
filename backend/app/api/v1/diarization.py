"""
Diarization API Routes
说话人识别接口
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.recording import Recording, Transcript
from app.models.user import User, UserConfig
from app.services.diarization_service import (
    DiarizationProvider,
    DiarizationService,
    convert_to_transcript_segments,
    format_diarization_transcript,
)
from app.utils.large_object import read_audio_data

router = APIRouter(prefix="/diarization", tags=["Diarization"])


class DiarizationRequest(BaseModel):
    provider: str | None = "assemblyai"  # assemblyai, deepgram
    expected_speakers: int | None = None  # Hint for number of speakers


class SpeakerSegmentResponse(BaseModel):
    start: float
    end: float
    text: str
    speaker: str
    confidence: float


class DiarizationResponse(BaseModel):
    recording_id: UUID
    full_text: str
    formatted_text: str  # With speaker labels
    segments: list[SpeakerSegmentResponse]
    speakers: list[str]
    language: str


@router.post("/{recording_id}", response_model=DiarizationResponse)
async def run_diarization(
    recording_id: UUID,
    request: DiarizationRequest = DiarizationRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    对录音进行说话人识别

    使用云 API (AssemblyAI 或 Deepgram) 识别音频中的不同说话人，
    并将转录内容标记为不同说话人的片段。

    自动使用用户的 STT API Key（如果 STT 提供商支持说话人识别）。
    在设置页面配置 STT 时，选择 AssemblyAI 或 Deepgram 作为提供商即可。
    """
    # Get recording with audio
    result = await db.execute(
        select(Recording)
        .where(Recording.id == recording_id, Recording.user_id == current_user.id)
        .options(selectinload(Recording.transcript))
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="录音不存在")

    # Check if audio exists
    if not recording.audio_oid and not recording.audio_blob_id:
        raise HTTPException(status_code=400, detail="录音没有音频数据")

    # Read audio data
    audio_data = await read_audio_data(db, oid=recording.audio_oid, blob_id=recording.audio_blob_id)

    if not audio_data:
        raise HTTPException(status_code=404, detail="无法读取音频数据")

    # Get user config
    config_result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    user_config = config_result.scalar_one_or_none()

    # Determine provider
    try:
        provider = DiarizationProvider(request.provider)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的提供商: {request.provider}。支持: assemblyai, deepgram",
        )

    # Run diarization
    try:
        diarization_service = DiarizationService(user_config)
        result = await diarization_service.diarize(
            audio_data=audio_data,
            language=recording.source_lang,
            expected_speakers=request.expected_speakers,
            provider=provider,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"说话人识别失败: {str(e)}")

    # Update transcript with diarization results
    if recording.transcript:
        recording.transcript.segments = convert_to_transcript_segments(result)
        recording.transcript.full_text = result.full_text
    else:
        # Create new transcript
        transcript = Transcript(
            recording_id=recording_id,
            segments=convert_to_transcript_segments(result),
            full_text=result.full_text,
            language=result.language,
        )
        db.add(transcript)

    await db.commit()

    # Format response
    formatted_text = format_diarization_transcript(result)

    return DiarizationResponse(
        recording_id=recording_id,
        full_text=result.full_text,
        formatted_text=formatted_text,
        segments=[
            SpeakerSegmentResponse(
                start=seg.start,
                end=seg.end,
                text=seg.text,
                speaker=seg.speaker,
                confidence=seg.confidence,
            )
            for seg in result.segments
        ],
        speakers=result.speakers,
        language=result.language,
    )


@router.get("/providers")
async def get_available_providers(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """获取可用的说话人识别提供商列表（基于用户 STT 配置）"""
    import os

    # Get user config
    config_result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    user_config = config_result.scalar_one_or_none()

    providers = []

    # Check if user's STT config supports diarization
    stt_provider = (user_config.stt_provider or "").lower() if user_config else ""
    stt_base_url = (user_config.stt_base_url or "").lower() if user_config else ""
    has_stt_key = bool(user_config and user_config.stt_api_key)

    # AssemblyAI
    assemblyai_from_config = (
        "assemblyai" in stt_provider or "assembly" in stt_provider or "assemblyai" in stt_base_url
    )
    assemblyai_from_env = bool(os.environ.get("ASSEMBLYAI_API_KEY"))

    providers.append(
        {
            "id": "assemblyai",
            "name": "AssemblyAI",
            "configured": assemblyai_from_config and has_stt_key or assemblyai_from_env,
            "description": "高精度说话人识别，支持多种语言"
            if (assemblyai_from_config and has_stt_key) or assemblyai_from_env
            else "在设置中配置 STT 提供商为 AssemblyAI",
        }
    )

    # Deepgram
    deepgram_from_config = "deepgram" in stt_provider or "deepgram" in stt_base_url
    deepgram_from_env = bool(os.environ.get("DEEPGRAM_API_KEY"))

    providers.append(
        {
            "id": "deepgram",
            "name": "Deepgram",
            "configured": deepgram_from_config and has_stt_key or deepgram_from_env,
            "description": "实时转录和说话人识别"
            if (deepgram_from_config and has_stt_key) or deepgram_from_env
            else "在设置中配置 STT 提供商为 Deepgram",
        }
    )

    return {"providers": providers}
