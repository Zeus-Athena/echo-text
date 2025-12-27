"""
STT Service
语音转文字服务
"""

import os
import tempfile

import httpx
from loguru import logger
from openai import AsyncOpenAI

from app.core.config import settings
from app.models.user import UserConfig


class STTService:
    """Speech-to-Text Service"""

    # Provider-specific configurations
    PROVIDER_CONFIGS = {
        "deepgram": {
            "base_url": "https://api.deepgram.com/v1",
            "model": "nova-3-general",
        },
        "groq": {
            "base_url": "https://api.groq.com/openai/v1",
            "model": "whisper-large-v3-turbo",
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "model": "whisper-1",
        },
        "siliconflow": {
            "base_url": "https://api.siliconflow.cn/v1",
            "model": "FunAudioLLM/SenseVoiceSmall",
        },
    }

    def __init__(self, config: UserConfig | None = None):
        """Initialize with user config or defaults"""
        # Determine active key based on provider
        if config:
            self.provider = (config.stt_provider or "").lower()
            logger.info(f"STTService Init: Provider={self.provider}")

            # Get provider-specific defaults
            provider_config = self.PROVIDER_CONFIGS.get(self.provider, {})
            default_base_url = provider_config.get("base_url", settings.DEFAULT_STT_BASE_URL)
            default_model = provider_config.get("model", settings.DEFAULT_STT_MODEL)

            # Use config values if provided, otherwise use provider-specific defaults
            self.model = config.stt_model or default_model
            self.base_url = config.stt_base_url or default_base_url

            if self.provider == "deepgram":
                self.api_key = config.stt_deepgram_api_key
                logger.info(
                    f"Selected Deepgram Key: {self.api_key[:4] + '***' if self.api_key else 'None'}"
                )
            elif self.provider == "groq":
                self.api_key = config.stt_groq_api_key
            elif self.provider == "openai":
                self.api_key = config.stt_openai_api_key
            elif self.provider == "siliconflow":
                self.api_key = config.stt_siliconflow_api_key
            else:
                self.api_key = config.stt_api_key
                logger.info(
                    f"Selected Default Key: {self.api_key[:4] + '***' if self.api_key else 'None'}"
                )
        else:
            self.api_key = None
            self.base_url = settings.DEFAULT_STT_BASE_URL
            self.model = settings.DEFAULT_STT_MODEL
            self.provider = settings.DEFAULT_STT_PROVIDER.lower()

        # Initialize OpenAI client for compatible providers
        if self.api_key and self.provider != "deepgram":
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self.client = None

    async def transcribe(
        self, audio_data: bytes, language: str = "zh", filename: str = "audio.wav"
    ) -> dict:
        """
        Transcribe audio to text with timestamps
        """
        if not self.api_key:
            raise ValueError("STT not configured. Please set API key in settings.")

        # Handle Deepgram Native API
        if self.provider == "deepgram":
            return await self._transcribe_deepgram(audio_data, language)

        # Handle OpenAI Compatible API
        if not self.client:
            # Should be caught by check above, but for safety
            raise ValueError(f"STT Client not initialized for provider {self.provider}")

        try:
            # Create a temporary file for the audio
            suffix = os.path.splitext(filename)[1] or ".wav"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
                tmp_file.write(audio_data)
                tmp_path = tmp_file.name

            try:
                # Open and transcribe
                with open(tmp_path, "rb") as audio_file:
                    logger.info(
                        f"STT Request: Model={self.model}, BaseURL={self.base_url}, Key={self.api_key[:4] + '***' if self.api_key else 'None'}"
                    )
                    response = await self.client.audio.transcriptions.create(
                        model=self.model,
                        file=audio_file,
                        language=language if language != "auto" else None,
                        response_format="verbose_json",
                        timestamp_granularities=["segment"],
                    )

                # Parse response
                segments = []
                if hasattr(response, "segments") and response.segments:
                    for seg in response.segments:
                        # Handle both object and dict (just in case)
                        if isinstance(seg, dict):
                            segments.append(
                                {
                                    "start": seg.get("start", 0),
                                    "end": seg.get("end", 0),
                                    "text": seg.get("text", "").strip(),
                                }
                            )
                        else:
                            segments.append(
                                {
                                    "start": getattr(seg, "start", 0),
                                    "end": getattr(seg, "end", 0),
                                    "text": getattr(seg, "text", "").strip(),
                                }
                            )

                # Normalize first segment to start at 0.0
                if segments:
                    segments[0]["start"] = 0.0

                return {
                    "text": response.text if hasattr(response, "text") else str(response),
                    "segments": segments,
                    "language": response.language if hasattr(response, "language") else language,
                }
            finally:
                # Clean up temp file
                os.unlink(tmp_path)

        except Exception as e:
            logger.error(f"STT transcription error: {e}")
            raise

    async def _transcribe_deepgram(self, audio_data: bytes, language: str) -> dict:
        """Transcribe using Deepgram Native API"""

        url = "https://api.deepgram.com/v1/listen"
        params = {
            "model": self.model or "nova-3-general",
            "smart_format": "true",
            "punctuate": "true",
            "diarize": "false",
        }
        if language and language != "auto":
            params["language"] = language

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/wav",  # Defaulting to wav, Deepgram usually detects
        }

        logger.info(f"Deepgram STT Request: Model={params['model']}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, params=params, headers=headers, content=audio_data, timeout=60.0
            )

        if response.status_code != 200:
            logger.error(f"Deepgram Error: {response.status_code} - {response.text}")
            raise Exception(f"Deepgram API Error: {response.status_code}")

        data = response.json()

        # Parse Deepgram Response
        # Structure: results -> channels[0] -> alternatives[0] -> paragraphs -> sentences
        result = data.get("results", {})
        channels = result.get("channels", [])
        if not channels:
            return {"text": "", "segments": [], "language": language}

        alternative = channels[0].get("alternatives", [])[0]
        text = alternative.get("transcript", "")

        segments = []

        # Try to use paragraphs for coarser segmentation (Paragraph-level)
        if "paragraphs" in alternative and "paragraphs" in alternative["paragraphs"]:
            for paragraph in alternative["paragraphs"]["paragraphs"]:
                sentences = paragraph.get("sentences", [])
                if not sentences:
                    continue

                # Group all sentences in the paragraph into one segment
                # Join with space, ensuring no double spaces
                para_text = " ".join([s.get("text", "").strip() for s in sentences]).strip()
                para_start = sentences[0].get("start", 0)
                para_end = sentences[-1].get("end", 0)

                segments.append({"start": para_start, "end": para_end, "text": para_text})
        # Fallback to pure words if no paragraphs (unlikely with smart_format=true)
        elif "words" in alternative:
            words = alternative.get("words", [])
            for word in words:
                segments.append({"start": word["start"], "end": word["end"], "text": word["word"]})
        else:
            # Just use the full text as one segment if no other info
            if text:
                segments.append(
                    {
                        "start": 0.0,
                        "end": alternative.get("words", [{}])[-1].get("end", 0.0)
                        if alternative.get("words")
                        else 0.0,
                        "text": text,
                    }
                )

        # Get detected language from metadata, fallback to input language
        detected_language = language
        if "metadata" in data and "language" in data["metadata"]:
            detected_language = data["metadata"].get("language", language)

        # Normalize first segment to start at 0.0
        if segments:
            segments[0]["start"] = 0.0

        return {"text": text, "segments": segments, "language": detected_language}

    async def check_balance(self) -> dict:
        """Check account balance for current provider"""
        if not self.api_key:
            return {"error": "API Key not configured"}

        try:
            if self.provider == "deepgram":
                async with httpx.AsyncClient() as client:
                    # Step 1: Get project ID
                    projects_resp = await client.get(
                        "https://api.deepgram.com/v1/projects",
                        headers={"Authorization": f"Token {self.api_key}"},
                        timeout=10.0,
                    )
                    if projects_resp.status_code != 200:
                        return {"error": f"Projects API Error: {projects_resp.status_code}"}

                    projects = projects_resp.json().get("projects", [])
                    if not projects:
                        return {"error": "No Deepgram projects found"}

                    project_id = projects[0].get("project_id")

                    # Step 2: Get balance
                    balance_resp = await client.get(
                        f"https://api.deepgram.com/v1/projects/{project_id}/balances",
                        headers={"Authorization": f"Token {self.api_key}"},
                        timeout=10.0,
                    )
                    if balance_resp.status_code != 200:
                        return {"error": f"Balance API Error: {balance_resp.status_code}"}

                    balances = balance_resp.json().get("balances", [])
                    if not balances:
                        return {"message": "No balance info available"}

                    total = sum(float(b.get("amount", 0)) for b in balances)
                    return {"balance": total, "currency": "USD", "provider": "Deepgram"}

            elif self.provider == "siliconflow":
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        "https://api.siliconflow.cn/v1/user/info",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        timeout=10.0,
                    )
                    if resp.status_code == 200:
                        balance = resp.json().get("data", {}).get("balance")
                        return {
                            "balance": float(balance) if balance else 0,
                            "currency": "CNY",
                            "provider": "SiliconFlow",
                        }
                    return {"error": f"API Error: {resp.status_code}"}

            return {"message": f"Balance check not supported for: {self.provider}"}

        except Exception as e:
            logger.error(f"STT balance check failed: {e}")
            return {"error": str(e)}

    async def transcribe_file(self, file_path: str, language: str = "zh") -> dict:
        """Transcribe audio file"""
        with open(file_path, "rb") as f:
            audio_data = f.read()

        filename = os.path.basename(file_path)
        return await self.transcribe(audio_data, language, filename)


async def get_stt_service(config: UserConfig | None = None) -> STTService:
    """Get STT service instance"""
    return STTService(config)
