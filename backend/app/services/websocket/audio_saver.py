"""
Audio Saver
音频保存处理器 - 负责转码和持久化
"""

from __future__ import annotations

import asyncio
import os
import tempfile

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recording import Recording
from app.utils.audio_utils import compress_to_opus, convert_webm_to_wav, get_audio_duration
from app.utils.large_object import save_audio_data


class AudioSaver:
    """音频保存处理器"""

    DEFAULT_TIMEOUT = 60  # 转码超时时间（秒）

    def __init__(self, db: AsyncSession, timeout: int = DEFAULT_TIMEOUT):
        self.db = db
        self.timeout = timeout

    async def save(
        self,
        processor,
        recording_id: str,
    ) -> dict:
        """
        保存音频到数据库

        Args:
            processor: 音频处理器实例（需要有 stop() 方法）
            recording_id: 录音 ID

        Returns:
            {"success": bool, "size": int, "format": str, "error": str?}
        """
        try:
            # 获取音频数据
            header, all_audio = await processor.stop()

            if not all_audio:
                return {"success": False, "error": "No audio data"}

            # 确保 header 在前
            if header and not all_audio.startswith(header):
                all_audio = header + all_audio

            # 转码
            wav_data, final_audio, audio_format = await self._convert(all_audio)

            if not final_audio:
                return {"success": False, "error": "Audio conversion failed"}

            # 保存到数据库
            audio_oid, audio_blob_id = await save_audio_data(self.db, final_audio)

            # 获取时长
            duration = await self._get_duration(wav_data)

            # 更新 Recording 记录
            await self._update_recording(
                recording_id,
                audio_oid,
                audio_blob_id,
                len(final_audio),
                audio_format,
                duration,
            )

            return {
                "success": True,
                "size": len(final_audio),
                "format": audio_format,
                "duration": duration,
            }

        except Exception as e:
            logger.error(f"Error saving audio: {e}")
            return {"success": False, "error": str(e)}

    async def _convert(
        self,
        raw_audio: bytes,
    ) -> tuple[bytes | None, bytes | None, str]:
        """
        转换音频格式: WebM -> WAV -> Opus

        Returns:
            (wav_data, final_audio, format)
        """
        loop = asyncio.get_event_loop()
        wav_data = None
        final_audio = None
        audio_format = "opus"

        try:
            # WebM -> WAV
            wav_data = await asyncio.wait_for(
                loop.run_in_executor(None, convert_webm_to_wav, raw_audio),
                timeout=self.timeout,
            )

            # WAV -> Opus
            final_audio = await asyncio.wait_for(
                loop.run_in_executor(None, compress_to_opus, wav_data, "48k"),
                timeout=self.timeout,
            )

        except TimeoutError:
            logger.warning("Audio conversion timeout, saving raw WebM")
            final_audio = raw_audio
            audio_format = "webm"
        except Exception as e:
            logger.warning(f"Audio conversion failed: {e}, saving raw WebM")
            final_audio = raw_audio
            audio_format = "webm"

        return wav_data, final_audio, audio_format

    async def _get_duration(self, wav_data: bytes | None) -> int:
        """获取音频时长（秒）"""
        if not wav_data:
            return 0

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(wav_data)
                tmp_path = tmp.name

            duration = get_audio_duration(tmp_path)
            os.unlink(tmp_path)
            return int(duration) if duration else 0
        except Exception:
            return 0

    async def _update_recording(
        self,
        recording_id: str,
        audio_oid: int | None,
        audio_blob_id: str | None,
        audio_size: int,
        audio_format: str,
        duration: int,
    ):
        """更新 Recording 记录"""
        result = await self.db.execute(select(Recording).where(Recording.id == recording_id))
        recording = result.scalar_one_or_none()

        if recording:
            recording.audio_oid = audio_oid
            recording.audio_blob_id = audio_blob_id
            recording.audio_size = audio_size
            recording.audio_format = audio_format
            if duration > 0:
                recording.duration_seconds = duration
            await self.db.commit()
            logger.info(f"Recording {recording_id} updated: {audio_size} bytes, {audio_format}")
