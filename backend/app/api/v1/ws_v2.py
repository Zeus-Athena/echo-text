"""
WebSocket API Routes V2
实时通信接口 - 策略模式重构版 (Refactored)

使用模块化设计:
- ConnectionManager: 连接管理
- TranslationHandler: 翻译策略
- AudioSaver: 音频保存
- TranscriptionSession: 会话状态
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from sqlalchemy import select
from starlette.websockets import WebSocketState

from app.core.database import async_session
from app.models.recording import Transcript
from app.models.user import User, UserConfig
from app.services.audio_processors import (
    BaseAudioProcessor,
    ProcessorConfig,
    ProcessorFactory,
    TranscriptEvent,
)
from app.services.llm_service import LLMService
from app.services.stt_service import STTService
from app.services.websocket import (
    AudioSaver,
    TranscriptionSession,
    TranslationHandler,
)
from app.services.websocket.connection_manager import manager

router = APIRouter(prefix="/ws", tags=["WebSocket V2"])


async def append_transcript_to_db(
    db,
    recording_id,
    text: str,
    start_time: float = 0,
    end_time: float = 0,
    is_final: bool = True,
    speaker: str | None = None,
):
    """Append transcript to database in real-time (only final segments are saved)"""
    from sqlalchemy.orm.attributes import flag_modified

    if not recording_id:
        return

    # Only save final segments to database to avoid too many cards
    if not is_final:
        return

    try:
        result = await db.execute(select(Transcript).where(Transcript.recording_id == recording_id))
        transcript = result.scalar_one_or_none()

        new_segment = {
            "text": text,
            "start": start_time,
            "end": end_time,
            "is_final": is_final,
        }
        if speaker:
            new_segment["speaker"] = speaker

        if transcript:
            transcript.full_text = (transcript.full_text or "") + " " + text
            segments = list(transcript.segments or [])  # Create a new list
            segments.append(new_segment)
            transcript.segments = segments  # Assign new list
            flag_modified(transcript, "segments")  # Explicitly mark as modified
        else:
            transcript = Transcript(
                recording_id=recording_id,
                full_text=text,
                segments=[new_segment],
            )
            db.add(transcript)

        await db.commit()
        logger.debug(f"Transcript appended to DB for recording {recording_id}")
    except Exception as e:
        logger.error(f"Failed to append transcript to DB: {e}")


def get_api_key_for_provider(user_config, provider: str) -> str:
    """根据 provider 获取对应的 API Key"""
    provider_lower = (provider or "").lower()
    if provider_lower == "deepgram":
        return user_config.stt_deepgram_api_key or ""
    elif provider_lower == "groq":
        return user_config.stt_groq_api_key or ""
    elif provider_lower == "openai":
        return user_config.stt_openai_api_key or ""
    elif provider_lower == "siliconflow":
        return user_config.stt_siliconflow_api_key or ""
    return user_config.stt_api_key or ""


@router.websocket("/transcribe/v2/{token}")
async def websocket_transcribe_v2(websocket: WebSocket, token: str):
    """
    Real-time transcription WebSocket endpoint (V2 - Refactored).

    自动根据用户配置的 STT Provider 选择处理策略:
    - Groq/OpenAI -> SimulatedStreamingProcessor
    - Deepgram -> TrueStreamingProcessor
    """
    from app.api.deps import get_effective_config, verify_token

    # === 1. Token 验证 ===
    try:
        user_data = verify_token(token)
        user_id = user_data.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # === 2. 建立连接 ===
    client_id = f"{user_id}_{id(websocket)}"
    await manager.connect(websocket, client_id)

    # 会话状态
    session = TranscriptionSession(client_id=client_id, user_id=user_id)
    processor: BaseAudioProcessor | None = None
    translator: TranslationHandler | None = None
    audio_saver: AudioSaver | None = None

    # 翻译任务管理
    translation_queue: asyncio.Queue | None = None
    translation_task: asyncio.Task | None = None

    try:
        async with async_session() as db:
            # === 3. 获取用户配置 ===
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()

            if not user:
                await websocket.close(code=4001, reason="User not found")
                return

            user_config = await get_effective_config(user, db)
            llm_service = LLMService(user_config)
            stt_service = STTService(user_config)
            audio_saver = AudioSaver(db)

            # 用户偏好
            own_config_result = await db.execute(
                select(UserConfig).where(UserConfig.user_id == user_id)
            )
            own_config = own_config_result.scalar_one_or_none()

            buffer_duration = float(own_config.audio_buffer_duration if own_config else 6.0)
            if buffer_duration < 0:
                buffer_duration = 0.0
            session.buffer_duration = buffer_duration
            session.silence_threshold = own_config.silence_threshold if own_config else 30.0

            provider = user_config.stt_provider or "Groq"
            model = user_config.stt_model or "whisper-large-v3-turbo"

            logger.info(f"WebSocket V2 started: user={user_id}, provider={provider}")

            # === 4. 音频保存辅助函数 ===
            async def save_audio():
                if session.audio_saved or not processor or not session.recording_id:
                    return

                await manager.send_status(client_id, "正在保存音频...")

                result = await audio_saver.save(processor, session.recording_id)

                if result["success"]:
                    session.mark_audio_saved()
                    await manager.send_json(
                        client_id,
                        {
                            "type": "audio_saved",
                            "recording_id": str(session.recording_id),
                            "audio_size": result["size"],
                        },
                    )
                else:
                    await manager.send_error(client_id, f"音频保存失败: {result.get('error')}")

            # === 5. 后台翻译工作线程 ===
            async def translation_worker(queue: asyncio.Queue, handler: TranslationHandler):
                """从队列读取转录事件进行翻译，避免阻塞主 WS 循环"""
                try:
                    while True:
                        event = await queue.get()
                        try:
                            # 传递 transcript_id 以便前端关联
                            results = await handler.handle_transcript(
                                event.text, event.is_final, event.transcript_id
                            )
                            for result in results:
                                await manager.send_translation(
                                    client_id,
                                    result["text"],
                                    result["is_final"],
                                    result.get("transcript_id", ""),
                                )
                        except Exception as e:
                            logger.error(f"Translation worker error: {e}")
                        finally:
                            queue.task_done()
                except asyncio.CancelledError:
                    pass

            # === 6. 转录回调 ===
            async def on_transcript(event: TranscriptEvent):
                # 发送转录结果 (立即发送，无阻塞) - 包含精确时间戳和 transcript_id
                await manager.send_transcript(
                    client_id,
                    event.text,
                    event.is_final,
                    event.speaker,
                    event.start_time,
                    event.end_time,
                    event.transcript_id,
                )

                # 持久化到数据库 (Async, Fast)
                await append_transcript_to_db(
                    db,
                    session.recording_id,
                    event.text,
                    event.start_time,
                    event.end_time,
                    event.is_final,
                    event.speaker,
                )

                # 放入翻译队列 (Non-blocking)
                if translation_queue and translator:
                    translation_queue.put_nowait(event)

            async def on_error(message: str):
                await manager.send_error(client_id, message)

            # === 7. 消息循环 ===
            while True:
                try:
                    message = await websocket.receive()

                    # 二进制音频数据
                    if "bytes" in message:
                        if session.is_recording and processor:
                            await processor.process_audio(message["bytes"])

                    # JSON 命令
                    elif "text" in message:
                        data = json.loads(message["text"])
                        action = data.get("action")

                        if action == "start":
                            session.start_recording(
                                recording_id=data.get("recording_id"),
                                source_lang=data.get("source_lang", "en"),
                                target_lang=data.get("target_lang", "zh"),
                                silence_threshold=data.get("silence_threshold"),
                            )

                            # 创建翻译处理器
                            # 伪流式（Groq/OpenAI）：STT 弹性窗口已控制频率，直接翻译
                            # 真流式（Deepgram）：使用 translation_mode 配置
                            if provider in ["Deepgram"]:
                                translation_buffer = float(
                                    own_config.translation_mode if own_config else 0
                                )
                            else:
                                translation_buffer = 0.0  # 伪流式直接翻译

                            translator = TranslationHandler(
                                llm_service=llm_service,
                                buffer_duration=translation_buffer,
                                source_lang=session.source_lang,
                                target_lang=session.target_lang,
                            )

                            # 启动后台翻译任务
                            translation_queue = asyncio.Queue()
                            translation_task = asyncio.create_task(
                                translation_worker(translation_queue, translator)
                            )

                            # 创建音频处理器
                            api_key = get_api_key_for_provider(user_config, provider)
                            proc_config = ProcessorConfig(
                                provider=provider,
                                model=model,
                                source_lang=session.source_lang,
                                target_lang=session.target_lang,
                                api_key=api_key,
                                api_base_url=user_config.stt_base_url or "",
                                silence_threshold=session.silence_threshold,
                                buffer_duration=session.buffer_duration,
                                diarization=data.get("diarization", False),
                                smart_format=True,
                                interim_results=True,
                            )

                            processor = ProcessorFactory.create(
                                config=proc_config,
                                stt_service=stt_service,
                                on_transcript=on_transcript,
                                on_error=on_error,
                            )
                            await processor.start()

                            await manager.send_status(
                                client_id, f"Recording started (Provider: {provider})"
                            )
                            logger.info(f"Recording started: provider={provider}")

                        elif action == "ping":
                            await manager.send_pong(client_id)

                        elif action == "pause":
                            if processor and hasattr(processor, "pause"):

                                async def on_auto_stop():
                                    session.stop_recording()
                                    await save_audio()
                                    await manager.send_json(
                                        client_id,
                                        {
                                            "type": "auto_stopped",
                                            "reason": "pause_timeout",
                                        },
                                    )

                                await processor.pause(on_auto_stop)
                            await manager.send_status(client_id, "Recording paused")

                        elif action == "resume":
                            if processor and hasattr(processor, "resume"):
                                await processor.resume()
                            await manager.send_status(client_id, "Recording resumed")

                        elif action == "stop":
                            session.stop_recording()

                            # 停止翻译任务确保数据处理完毕
                            if translation_task:
                                # 等待队列排空 (但给个超时防止死锁)
                                if translation_queue:
                                    try:
                                        # 简单等待队列为空
                                        while not translation_queue.empty():
                                            await asyncio.sleep(0.1)
                                    except Exception:
                                        pass

                                # 刷新翻译缓冲区 (Flush)
                                if translator:
                                    flush_results = await translator.flush()
                                    for result in flush_results:
                                        await manager.send_translation(
                                            client_id,
                                            result["text"],
                                            result["is_final"],
                                            result.get("transcript_id", ""),
                                        )

                                # 取消任务
                                translation_task.cancel()
                                try:
                                    await translation_task
                                except asyncio.CancelledError:
                                    pass
                                translation_task = None
                                translation_queue = None

                            await save_audio()
                            await manager.send_status(client_id, "Recording stopped")

                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected: {client_id}")
                    break
                except RuntimeError as e:
                    # 检查连接状态
                    if websocket.client_state == WebSocketState.DISCONNECTED:
                        logger.info(f"WebSocket already closed: {client_id}")
                        break
                    logger.error(f"WebSocket runtime error: {e}")
                    await manager.send_error(client_id, str(e))
                except Exception as e:
                    logger.error(f"WebSocket error: {e}")
                    await manager.send_error(client_id, str(e))

    except Exception as e:
        logger.error(f"WebSocket session error: {e}")

    finally:
        # 清理翻译任务
        if translation_task and not translation_task.done():
            translation_task.cancel()
            try:
                await translation_task
            except asyncio.CancelledError:
                pass

        # 断开时保存音频
        # 修复: 只要有 recording_id 和 processor 就尝试保存，不依赖 is_recording
        # (因为 stop() 可能会先设置 is_recording=False，但如果在保存前 WS 断开，这里仍需补救)
        if session.recording_id and not session.audio_saved and processor:
            try:
                async with async_session() as db:
                    audio_saver = AudioSaver(db)
                    await audio_saver.save(processor, session.recording_id)
            except Exception as e:
                logger.error(f"Failed to save on disconnect: {e}")

        manager.disconnect(client_id)
