"""
TTS Service
文字转语音服务
"""

import os
import tempfile

from loguru import logger

from app.core.config import settings
from app.models.user import UserConfig


class TTSService:
    """Text-to-Speech Service"""

    def __init__(self, config: UserConfig | None = None):
        """Initialize with user config or defaults"""
        if config:
            self.provider = config.tts_provider or settings.DEFAULT_TTS_PROVIDER
            self.voice = config.tts_voice or settings.DEFAULT_TTS_VOICE
            self.api_key = config.tts_api_key
            self.base_url = config.tts_base_url
        else:
            self.provider = settings.DEFAULT_TTS_PROVIDER
            self.voice = settings.DEFAULT_TTS_VOICE
            self.api_key = None
            self.base_url = None

    async def synthesize(self, text: str, voice: str | None = None, speed: float = 1.0) -> bytes:
        """
        Synthesize speech from text

        Returns: Audio bytes (MP3 format)
        """
        voice = voice or self.voice

        if self.provider == "edge":
            return await self._synthesize_edge_tts(text, voice, speed)
        elif self.provider == "openai":
            return await self._synthesize_openai_tts(text, voice, speed)
        else:
            # Default to Edge TTS
            return await self._synthesize_edge_tts(text, voice, speed)

    async def _synthesize_edge_tts(self, text: str, voice: str, speed: float) -> bytes:
        """Use Edge TTS (free Microsoft TTS)"""
        try:
            import edge_tts

            # Adjust rate based on speed
            rate = f"+{int((speed - 1) * 100)}%" if speed >= 1 else f"{int((speed - 1) * 100)}%"

            communicate = edge_tts.Communicate(text, voice, rate=rate)

            # Create temp file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            try:
                await communicate.save(tmp_path)

                with open(tmp_path, "rb") as f:
                    audio_data = f.read()

                return audio_data
            finally:
                os.unlink(tmp_path)

        except Exception as e:
            logger.error(f"Edge TTS error: {e}")
            raise

    async def _synthesize_openai_tts(self, text: str, voice: str, speed: float) -> bytes:
        """Use OpenAI TTS"""
        if not self.api_key:
            raise ValueError("OpenAI TTS requires API key")

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=self.api_key, base_url=self.base_url or "https://api.openai.com/v1"
            )

            response = await client.audio.speech.create(
                model="tts-1", voice=voice, input=text, speed=speed
            )

            return response.content

        except Exception as e:
            logger.error(f"OpenAI TTS error: {e}")
            raise

    async def synthesize_to_file(
        self, text: str, output_path: str, voice: str | None = None, speed: float = 1.0
    ) -> str:
        """Synthesize and save to file"""
        audio_data = await self.synthesize(text, voice, speed)

        with open(output_path, "wb") as f:
            f.write(audio_data)

        return output_path

    @staticmethod
    def get_available_voices() -> list:
        """Get list of available Edge TTS voices"""
        return [
            # Chinese
            {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓 (女)", "lang": "zh-CN"},
            {"id": "zh-CN-YunxiNeural", "name": "云希 (男)", "lang": "zh-CN"},
            {"id": "zh-CN-YunjianNeural", "name": "云健 (男)", "lang": "zh-CN"},
            {"id": "zh-CN-XiaoyiNeural", "name": "晓伊 (女)", "lang": "zh-CN"},
            # English US
            {"id": "en-US-JennyNeural", "name": "Jenny (Female)", "lang": "en-US"},
            {"id": "en-US-GuyNeural", "name": "Guy (Male)", "lang": "en-US"},
            {"id": "en-US-AriaNeural", "name": "Aria (Female)", "lang": "en-US"},
            # English UK
            {"id": "en-GB-SoniaNeural", "name": "Sonia (Female)", "lang": "en-GB"},
            {"id": "en-GB-RyanNeural", "name": "Ryan (Male)", "lang": "en-GB"},
        ]


async def get_tts_service(config: UserConfig | None = None) -> TTSService:
    """Get TTS service instance"""
    return TTSService(config)
