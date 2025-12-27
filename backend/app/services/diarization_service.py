"""
Diarization Service
说话人识别服务 - 支持多种云 API
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx

from app.models.user import UserConfig


class DiarizationProvider(str, Enum):
    """Supported diarization providers"""

    ASSEMBLYAI = "assemblyai"
    DEEPGRAM = "deepgram"
    AZURE = "azure"


@dataclass
class SpeakerSegment:
    """A segment of speech with speaker identification"""

    start: float  # Start time in seconds
    end: float  # End time in seconds
    text: str  # Transcribed text
    speaker: str  # Speaker identifier (e.g., "Speaker 1", "Speaker 2")
    confidence: float = 1.0  # Confidence score


@dataclass
class DiarizationResult:
    """Result of diarization process"""

    full_text: str
    segments: list[SpeakerSegment]
    speakers: list[str]  # List of unique speaker identifiers
    language: str


class DiarizationService:
    """Speaker diarization service supporting multiple cloud providers"""

    def __init__(self, config: UserConfig | None = None):
        """
        Initialize with user config

        Uses the user's STT API key if the provider supports diarization.
        Supported providers: assemblyai, deepgram
        """
        self.config = config
        self.api_key = None
        self.provider = None

        # Load provider from user's STT config
        if config:
            stt_provider = (config.stt_provider or "").lower()

            # Check if STT provider supports diarization
            if "assemblyai" in stt_provider or "assembly" in stt_provider:
                self.provider = DiarizationProvider.ASSEMBLYAI
                self.api_key = config.stt_api_key
            elif "deepgram" in stt_provider:
                self.provider = DiarizationProvider.DEEPGRAM
                self.api_key = config.stt_api_key
            else:
                # Fall back to checking base_url for provider hints
                stt_base_url = (config.stt_base_url or "").lower()
                if "assemblyai" in stt_base_url:
                    self.provider = DiarizationProvider.ASSEMBLYAI
                    self.api_key = config.stt_api_key
                elif "deepgram" in stt_base_url:
                    self.provider = DiarizationProvider.DEEPGRAM
                    self.api_key = config.stt_api_key

        # Default to AssemblyAI if no provider detected from config
        if not self.provider:
            self.provider = DiarizationProvider.ASSEMBLYAI

    async def diarize(
        self,
        audio_data: bytes,
        language: str = "zh",
        expected_speakers: int | None = None,
        provider: DiarizationProvider | None = None,
    ) -> DiarizationResult:
        """
        Perform speaker diarization on audio

        Args:
            audio_data: Audio bytes
            language: Language code
            expected_speakers: Optional hint for number of speakers
            provider: Override default provider

        Returns:
            DiarizationResult with speaker-labeled segments
        """
        active_provider = provider or self.provider

        if active_provider == DiarizationProvider.ASSEMBLYAI:
            return await self._diarize_assemblyai(audio_data, language, expected_speakers)
        elif active_provider == DiarizationProvider.DEEPGRAM:
            return await self._diarize_deepgram(audio_data, language, expected_speakers)
        elif active_provider == DiarizationProvider.AZURE:
            return await self._diarize_azure(audio_data, language, expected_speakers)
        else:
            raise ValueError(f"Unsupported diarization provider: {active_provider}")

    async def _diarize_assemblyai(
        self, audio_data: bytes, language: str, expected_speakers: int | None
    ) -> DiarizationResult:
        """
        Diarization using AssemblyAI API
        https://www.assemblyai.com/docs/guides/speaker-diarization
        """
        api_key = self._get_api_key("ASSEMBLYAI_API_KEY")
        if not api_key:
            raise ValueError("AssemblyAI API key not configured")

        headers = {"authorization": api_key}

        async with httpx.AsyncClient(timeout=300.0) as client:
            # Step 1: Upload audio
            upload_response = await client.post(
                "https://api.assemblyai.com/v2/upload", headers=headers, content=audio_data
            )
            upload_response.raise_for_status()
            audio_url = upload_response.json()["upload_url"]

            # Step 2: Start transcription with diarization
            transcript_config = {
                "audio_url": audio_url,
                "speaker_labels": True,
                "language_code": self._map_language_assemblyai(language),
            }
            if expected_speakers:
                transcript_config["speakers_expected"] = expected_speakers

            transcript_response = await client.post(
                "https://api.assemblyai.com/v2/transcript", headers=headers, json=transcript_config
            )
            transcript_response.raise_for_status()
            transcript_id = transcript_response.json()["id"]

            # Step 3: Poll for completion
            while True:
                status_response = await client.get(
                    f"https://api.assemblyai.com/v2/transcript/{transcript_id}", headers=headers
                )
                status_response.raise_for_status()
                result = status_response.json()

                if result["status"] == "completed":
                    break
                elif result["status"] == "error":
                    raise Exception(f"AssemblyAI error: {result.get('error', 'Unknown error')}")

                await asyncio.sleep(3)  # Poll every 3 seconds

            # Step 4: Parse results
            segments = []
            speakers = set()

            for utterance in result.get("utterances", []):
                speaker = f"Speaker {utterance['speaker']}"
                speakers.add(speaker)
                segments.append(
                    SpeakerSegment(
                        start=utterance["start"] / 1000.0,  # Convert ms to seconds
                        end=utterance["end"] / 1000.0,
                        text=utterance["text"],
                        speaker=speaker,
                        confidence=utterance.get("confidence", 1.0),
                    )
                )

            return DiarizationResult(
                full_text=result.get("text", ""),
                segments=segments,
                speakers=sorted(list(speakers)),
                language=language,
            )

    async def _diarize_deepgram(
        self, audio_data: bytes, language: str, expected_speakers: int | None
    ) -> DiarizationResult:
        """
        Diarization using Deepgram API
        https://developers.deepgram.com/docs/diarization
        """
        api_key = self._get_api_key("DEEPGRAM_API_KEY")
        if not api_key:
            raise ValueError("Deepgram API key not configured")

        headers = {"Authorization": f"Token {api_key}", "Content-Type": "audio/wav"}

        # Build query params
        params = {
            "model": "nova-2",
            "diarize": "true",
            "punctuate": "true",
            "language": self._map_language_deepgram(language),
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen",
                headers=headers,
                params=params,
                content=audio_data,
            )
            response.raise_for_status()
            result = response.json()

        # Parse results
        segments = []
        speakers = set()

        alternatives = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [])
        if alternatives:
            words = alternatives[0].get("words", [])

            # Group words by speaker
            current_speaker = None
            current_segment = {"start": 0, "end": 0, "text": [], "speaker": ""}

            for word in words:
                speaker = f"Speaker {word.get('speaker', 0)}"

                if speaker != current_speaker:
                    # Save previous segment if exists
                    if current_segment["text"]:
                        speakers.add(current_segment["speaker"])
                        segments.append(
                            SpeakerSegment(
                                start=current_segment["start"],
                                end=current_segment["end"],
                                text=" ".join(current_segment["text"]),
                                speaker=current_segment["speaker"],
                                confidence=word.get("confidence", 1.0),
                            )
                        )

                    # Start new segment
                    current_speaker = speaker
                    current_segment = {
                        "start": word.get("start", 0),
                        "end": word.get("end", 0),
                        "text": [word.get("punctuated_word", word.get("word", ""))],
                        "speaker": speaker,
                    }
                else:
                    current_segment["end"] = word.get("end", 0)
                    current_segment["text"].append(
                        word.get("punctuated_word", word.get("word", ""))
                    )

            # Add final segment
            if current_segment["text"]:
                speakers.add(current_segment["speaker"])
                segments.append(
                    SpeakerSegment(
                        start=current_segment["start"],
                        end=current_segment["end"],
                        text=" ".join(current_segment["text"]),
                        speaker=current_segment["speaker"],
                    )
                )

        full_text = alternatives[0].get("transcript", "") if alternatives else ""

        return DiarizationResult(
            full_text=full_text,
            segments=segments,
            speakers=sorted(list(speakers)),
            language=language,
        )

    async def _diarize_azure(
        self, audio_data: bytes, language: str, expected_speakers: int | None
    ) -> DiarizationResult:
        """
        Diarization using Azure Speech Services
        https://learn.microsoft.com/en-us/azure/ai-services/speech-service/get-started-stt-diarization

        Note: Azure requires more complex setup with Speech SDK
        This is a placeholder for future implementation
        """
        raise NotImplementedError(
            "Azure diarization requires Speech SDK. Please use AssemblyAI or Deepgram for now."
        )

    def _get_api_key(self, env_var: str) -> str | None:
        """Get API key - prioritizes user config over environment variable"""
        # First check if we have API key from user config
        if self.api_key:
            return self.api_key
        # Fall back to environment variable
        import os

        return os.environ.get(env_var)

    def _map_language_assemblyai(self, language: str) -> str:
        """Map language code to AssemblyAI format"""
        mapping = {
            "zh": "zh",
            "en": "en",
            "ja": "ja",
            "ko": "ko",
            "de": "de",
            "fr": "fr",
            "es": "es",
        }
        return mapping.get(language, language)

    def _map_language_deepgram(self, language: str) -> str:
        """Map language code to Deepgram format"""
        mapping = {
            "zh": "zh-CN",
            "en": "en-US",
            "ja": "ja",
            "ko": "ko",
            "de": "de",
            "fr": "fr",
            "es": "es",
        }
        return mapping.get(language, language)


def format_diarization_transcript(result: DiarizationResult) -> str:
    """
    Format diarization result as readable transcript with speaker labels

    Example:
        Speaker 1: Hello, how are you?
        Speaker 2: I'm doing great, thank you!
    """
    lines = []
    current_speaker = None

    for segment in result.segments:
        if segment.speaker != current_speaker:
            current_speaker = segment.speaker
            lines.append(f"\n{segment.speaker}:")
        lines.append(f"  {segment.text}")

    return "\n".join(lines).strip()


def convert_to_transcript_segments(result: DiarizationResult) -> list[dict[str, Any]]:
    """
    Convert diarization result to transcript segment format
    for storage in Transcript model
    """
    return [
        {
            "start": seg.start,
            "end": seg.end,
            "text": seg.text,
            "speaker": seg.speaker,
            "confidence": seg.confidence,
        }
        for seg in result.segments
    ]
