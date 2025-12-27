"""
Translation Schemas
翻译相关的请求/响应模型
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

# ========== Text Translation ==========


class TextTranslateRequest(BaseModel):
    """Text translation request"""

    text: str
    source_lang: str = "auto"
    target_lang: str = "en"
    style: str = "standard"  # standard, formal, casual


class TextTranslateResponse(BaseModel):
    """Text translation response"""

    original_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    llm_model: str | None = None


class TextTranslationHistory(BaseModel):
    """Text translation history item"""

    id: UUID
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    created_at: datetime

    class Config:
        from_attributes = True


# ========== Dictionary ==========


class DictionaryDefinition(BaseModel):
    """Single definition"""

    part_of_speech: str  # noun, verb, adj, etc.
    definition: str
    example: str | None = None


class DictionaryResponse(BaseModel):
    """Dictionary lookup response"""

    word: str
    phonetic: str | None = None
    audio_url: str | None = None  # Pronunciation audio
    definitions: list[DictionaryDefinition]
    phrases: list[str] = []
    synonyms: list[str] = []
    antonyms: list[str] = []


class VocabularyItem(BaseModel):
    """Vocabulary book item"""

    id: UUID
    word: str
    language: str
    created_at: datetime

    class Config:
        from_attributes = True


class AddToVocabularyRequest(BaseModel):
    """Add word to vocabulary request"""

    word: str
    language: str = "en"


# ========== TTS ==========


class TTSRequest(BaseModel):
    """TTS request"""

    text: str
    voice: str | None = None  # Use user's default if not specified
    speed: float = 1.0


class TTSResponse(BaseModel):
    """TTS response"""

    audio_url: str
    duration_seconds: float
