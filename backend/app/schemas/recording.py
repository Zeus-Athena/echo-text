"""
Recording Schemas
录音相关的请求/响应模型
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ========== Segment Schemas ==========


class TranscriptSegment(BaseModel):
    """Single transcript segment"""

    start: float  # Start time in seconds
    end: float  # End time in seconds
    text: str


# ========== Folder Schemas ==========


class FolderCreate(BaseModel):
    """Create folder request"""

    name: str = Field(max_length=100)
    parent_id: UUID | None = None
    source_type: str = "realtime"


class FolderResponse(BaseModel):
    """Folder response"""

    id: UUID
    name: str
    parent_id: UUID | None
    source_type: str = "realtime"
    recording_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class FolderListResponse(BaseModel):
    """Folder list with total recordings count"""

    folders: list[FolderResponse]
    total_recordings: int
    uncategorized_count: int


# ========== Tag Schemas ==========


class TagCreate(BaseModel):
    """Create tag request"""

    name: str = Field(max_length=50)
    color: str = "#3b82f6"


class TagResponse(BaseModel):
    """Tag response"""

    id: UUID
    name: str
    color: str

    class Config:
        from_attributes = True


# ========== Recording Schemas ==========


class RecordingCreate(BaseModel):
    """Create recording request"""

    title: str = Field(max_length=200)
    source_lang: str = "zh"
    target_lang: str = "en"
    folder_id: UUID | None = None


class RecordingUpdate(BaseModel):
    """Update recording request"""

    title: str | None = None
    folder_id: UUID | None = None
    tag_ids: list[UUID] | None = None


class TranscriptUpdate(BaseModel):
    """Update transcript request"""

    full_text: str
    segments: list[dict] | None = None


class TranslationUpdate(BaseModel):
    """Update translation request"""

    full_text: str
    segments: list[dict] | None = None


class RecordingListItem(BaseModel):
    """Recording list item"""

    id: UUID
    title: str
    duration_seconds: int
    source_lang: str
    target_lang: str
    status: str
    source_type: str = "realtime"
    has_summary: bool = False
    tags: list[TagResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class TranscriptResponse(BaseModel):
    """Transcript response"""

    id: UUID
    segments: list[TranscriptSegment]
    full_text: str | None
    language: str
    created_at: datetime

    class Config:
        from_attributes = True


class TranslationResponse(BaseModel):
    """Translation response"""

    id: UUID
    segments: list[TranscriptSegment]
    full_text: str | None
    target_lang: str
    llm_model: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class AISummaryResponse(BaseModel):
    """AI Summary response"""

    id: UUID
    summary: str | None
    key_points: list[str]
    action_items: list[str]
    auto_tags: list[str]
    chapters: list[dict] = []  # [{timestamp: int, title: str}]
    llm_model: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class RecordingDetail(BaseModel):
    """Full recording detail response"""

    id: UUID
    title: str
    s3_key: str | None
    audio_url: str | None = None
    audio_format: str = "opus"
    audio_size: int | None = None  # bytes
    duration_seconds: int
    source_lang: str
    target_lang: str
    status: str
    source_type: str = "realtime"
    folder_id: UUID | None
    tags: list[TagResponse]
    transcript: TranscriptResponse | None
    translation: TranslationResponse | None
    ai_summary: AISummaryResponse | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== Batch Operations ==========


class BatchDeleteRequest(BaseModel):
    """Batch delete request"""

    ids: list[UUID]


class BatchMoveRequest(BaseModel):
    """Batch move to folder request"""

    ids: list[UUID]
    folder_id: UUID | None


class BatchTagRequest(BaseModel):
    """Batch add tags request"""

    ids: list[UUID]
    tag_ids: list[UUID]
