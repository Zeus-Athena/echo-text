"""
ARQ Background Tasks
后台任务定义
"""

from uuid import UUID

from loguru import logger
from sqlalchemy import select

from app.core.database import async_session
from app.models.recording import Recording, Transcript, Translation
from app.services.llm_service import LLMService
from app.services.stt_service import STTService


async def transcribe_audio_task(
    ctx: dict,
    recording_id: str,
    audio_data: bytes,
    source_lang: str = "en",
    user_config_id: str | None = None,
) -> dict:
    """
    后台转录任务

    用于处理上传的音频文件，进行完整转录。
    适用于：
    - 用户上传音频文件
    - 重新转录已有录音
    """
    logger.info(f"[ARQ] Starting transcription for recording {recording_id}")

    try:
        # Get user config if provided
        user_config = None
        if user_config_id:
            async with async_session() as db:
                from app.models.user import UserConfig

                result = await db.execute(select(UserConfig).where(UserConfig.id == user_config_id))
                user_config = result.scalar_one_or_none()

        # Initialize STT service
        stt_service = STTService(user_config)

        # Perform transcription
        result = await stt_service.transcribe(
            audio_data, language=source_lang, filename="uploaded_audio.wav"
        )

        if not result.get("text"):
            logger.warning(f"[ARQ] Transcription returned empty for {recording_id}")
            return {"status": "completed", "text": "", "recording_id": recording_id}

        # Save transcript to database
        async with async_session() as db:
            # Check if transcript already exists
            existing = await db.execute(
                select(Transcript).where(Transcript.recording_id == UUID(recording_id))
            )
            transcript = existing.scalar_one_or_none()

            if transcript:
                transcript.full_text = result["text"]
                transcript.segments = result.get("segments", [])
            else:
                transcript = Transcript(
                    recording_id=UUID(recording_id),
                    full_text=result["text"],
                    segments=result.get("segments", []),
                )
                db.add(transcript)

            await db.commit()

        logger.info(
            f"[ARQ] Transcription completed for {recording_id}: {len(result['text'])} chars"
        )
        return {"status": "completed", "text": result["text"], "recording_id": recording_id}

    except Exception as e:
        logger.error(f"[ARQ] Transcription failed for {recording_id}: {e}")
        return {"status": "failed", "error": str(e), "recording_id": recording_id}


async def generate_summary_task(
    ctx: dict,
    recording_id: str,
    transcript: str,
    target_lang: str = "zh",
    user_config_id: str | None = None,
) -> dict:
    """
    后台生成摘要任务

    用于对转录文本生成 AI 摘要、关键点、待办事项等。
    """
    logger.info(f"[ARQ] Starting summary generation for recording {recording_id}")

    try:
        # Get user config if provided
        user_config = None
        if user_config_id:
            async with async_session() as db:
                from app.models.user import UserConfig

                result = await db.execute(select(UserConfig).where(UserConfig.id == user_config_id))
                user_config = result.scalar_one_or_none()

        # Initialize LLM service
        llm_service = LLMService(user_config)

        # Generate summary
        summary_result = await llm_service.generate_summary(
            transcript=transcript, target_lang=target_lang
        )

        # Update recording with summary
        async with async_session() as db:
            result = await db.execute(select(Recording).where(Recording.id == UUID(recording_id)))
            recording = result.scalar_one_or_none()

            if recording:
                recording.ai_summary = summary_result.get("summary", "")
                recording.key_points = summary_result.get("key_points", [])
                recording.action_items = summary_result.get("action_items", [])
                recording.auto_tags = summary_result.get("auto_tags", [])
                recording.chapters = summary_result.get("chapters", [])
                await db.commit()

        logger.info(f"[ARQ] Summary generated for {recording_id}")
        return {"status": "completed", "recording_id": recording_id, "summary": summary_result}

    except Exception as e:
        logger.error(f"[ARQ] Summary generation failed for {recording_id}: {e}")
        return {"status": "failed", "error": str(e), "recording_id": recording_id}


async def translate_transcript_task(
    ctx: dict,
    recording_id: str,
    transcript: str,
    source_lang: str = "en",
    target_lang: str = "zh",
    user_config_id: str | None = None,
) -> dict:
    """
    后台翻译任务

    用于翻译完整的转录文本。
    """
    logger.info(f"[ARQ] Starting translation for recording {recording_id}")

    try:
        # Get user config if provided
        user_config = None
        if user_config_id:
            async with async_session() as db:
                from app.models.user import UserConfig

                result = await db.execute(select(UserConfig).where(UserConfig.id == user_config_id))
                user_config = result.scalar_one_or_none()

        # Initialize LLM service
        llm_service = LLMService(user_config)

        # Translate
        translated_text = await llm_service.translate(
            transcript, source_lang=source_lang, target_lang=target_lang
        )

        # Save translation to database
        async with async_session() as db:
            # Check if translation already exists
            existing = await db.execute(
                select(Translation).where(Translation.recording_id == UUID(recording_id))
            )
            translation = existing.scalar_one_or_none()

            if translation:
                translation.full_text = translated_text
                translation.target_lang = target_lang
            else:
                translation = Translation(
                    recording_id=UUID(recording_id),
                    full_text=translated_text,
                    target_lang=target_lang,
                )
                db.add(translation)

            await db.commit()

        logger.info(f"[ARQ] Translation completed for {recording_id}")
        return {
            "status": "completed",
            "recording_id": recording_id,
            "translated_text": translated_text,
        }

    except Exception as e:
        logger.error(f"[ARQ] Translation failed for {recording_id}: {e}")
        return {"status": "failed", "error": str(e), "recording_id": recording_id}


async def process_uploaded_audio_task(
    ctx: dict, recording_id: str, user_config_id: str | None = None
) -> dict:
    """
    完整音频处理任务：转录 → 翻译 → AI分析

    用于处理用户上传的音频文件，一条龙后台执行。
    """
    logger.info(f"[ARQ] Starting full processing for recording {recording_id}")

    try:
        async with async_session() as db:
            # 获取录音信息
            result = await db.execute(select(Recording).where(Recording.id == UUID(recording_id)))
            recording = result.scalar_one_or_none()

            if not recording:
                logger.error(f"[ARQ] Recording not found: {recording_id}")
                return {"status": "failed", "error": "Recording not found"}

            # 更新状态：转录中
            recording.status = "transcribing"
            await db.commit()

            # 获取用户配置
            user_config = None
            if user_config_id:
                from app.models.user import UserConfig

                config_result = await db.execute(
                    select(UserConfig).where(UserConfig.user_id == user_config_id)
                )
                user_config = config_result.scalar_one_or_none()

            # 获取音频数据
            from app.utils.large_object import read_audio_data

            audio_data = await read_audio_data(
                db, oid=recording.audio_oid, blob_id=recording.audio_blob_id
            )

            if not audio_data:
                logger.error(f"[ARQ] No audio data for recording {recording_id}")
                recording.status = "failed"
                await db.commit()
                return {"status": "failed", "error": "No audio data"}

            # === Step 1: 转录 ===
            stt_service = STTService(user_config)
            stt_result = await stt_service.transcribe(
                audio_data, language=recording.source_lang or "en", filename="uploaded_audio.wav"
            )

            transcript_text = stt_result.get("text", "")
            if not transcript_text:
                logger.warning(f"[ARQ] Empty transcription for {recording_id}")
                recording.status = "failed"
                await db.commit()
                return {"status": "failed", "error": "Empty transcription"}

            # 保存转录结果
            existing_transcript = await db.execute(
                select(Transcript).where(Transcript.recording_id == UUID(recording_id))
            )
            transcript = existing_transcript.scalar_one_or_none()

            if transcript:
                transcript.full_text = transcript_text
                transcript.segments = stt_result.get("segments", [])
            else:
                transcript = Transcript(
                    recording_id=UUID(recording_id),
                    full_text=transcript_text,
                    segments=stt_result.get("segments", []),
                )
                db.add(transcript)

            await db.commit()
            logger.info(
                f"[ARQ] Transcription done for {recording_id}: {len(transcript_text)} chars"
            )

            # === Step 2: 翻译 ===
            recording.status = "translating"
            await db.commit()

            llm_service = LLMService(user_config)
            translated_text = await llm_service.translate(
                transcript_text,
                source_lang=recording.source_lang or "en",
                target_lang=recording.target_lang or "zh",
            )

            # 保存翻译结果
            existing_translation = await db.execute(
                select(Translation).where(Translation.recording_id == UUID(recording_id))
            )
            translation = existing_translation.scalar_one_or_none()

            if translation:
                translation.full_text = translated_text
                translation.target_lang = recording.target_lang or "zh"
            else:
                translation = Translation(
                    recording_id=UUID(recording_id),
                    full_text=translated_text,
                    target_lang=recording.target_lang or "zh",
                )
                db.add(translation)

            await db.commit()
            logger.info(f"[ARQ] Translation done for {recording_id}")

            # === Step 3: AI分析（可选，失败不影响整体） ===
            recording.status = "analyzing"
            await db.commit()

            try:
                summary_result = await llm_service.generate_summary(
                    transcript=transcript_text, target_lang=recording.target_lang or "zh"
                )

                recording.ai_summary = summary_result.get("summary", "")
                recording.key_points = summary_result.get("key_points", [])
                recording.action_items = summary_result.get("action_items", [])
                recording.auto_tags = summary_result.get("auto_tags", [])
                recording.chapters = summary_result.get("chapters", [])

                logger.info(f"[ARQ] AI analysis done for {recording_id}")
            except Exception as e:
                logger.warning(f"[ARQ] AI analysis failed for {recording_id}: {e}")
                # 不影响整体流程

            # 完成
            recording.status = "completed"
            await db.commit()

            logger.info(f"[ARQ] Full processing completed for {recording_id}")
            return {"status": "completed", "recording_id": recording_id}

    except Exception as e:
        logger.error(f"[ARQ] Processing failed for {recording_id}: {e}")
        # 尝试更新状态为失败
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(Recording).where(Recording.id == UUID(recording_id))
                )
                recording = result.scalar_one_or_none()
                if recording:
                    recording.status = "failed"
                    await db.commit()
        except Exception:
            pass
        return {"status": "failed", "error": str(e), "recording_id": recording_id}


async def startup(ctx: dict):
    """ARQ worker startup hook"""
    logger.info("[ARQ] Worker starting up...")


async def shutdown(ctx: dict):
    """ARQ worker shutdown hook"""
    logger.info("[ARQ] Worker shutting down...")


class WorkerSettings:
    """ARQ Worker Settings"""

    # Task functions
    functions = [
        transcribe_audio_task,
        generate_summary_task,
        translate_transcript_task,
        process_uploaded_audio_task,
    ]

    # Startup/shutdown hooks
    on_startup = startup
    on_shutdown = shutdown

    # Redis settings
    from app.workers.settings import REDIS_SETTINGS

    redis_settings = REDIS_SETTINGS

    # Worker config
    max_jobs = 10
    job_timeout = 300  # 5 minutes max per job
    keep_result = 3600  # Keep results for 1 hour
