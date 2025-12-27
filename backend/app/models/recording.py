"""
Recording Models
录音相关数据模型
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UUID


class Folder(Base):
    """Folder for organizing recordings"""

    __tablename__ = "folders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(), ForeignKey("folders.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source_type: Mapped[str] = mapped_column(String(20), default="realtime")  # realtime, upload

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="folders")
    recordings: Mapped[list["Recording"]] = relationship(
        "Recording", back_populates="folder", lazy="selectin"
    )


class Recording(Base):
    """Recording table"""

    __tablename__ = "recordings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(), ForeignKey("folders.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    s3_key: Mapped[str | None] = mapped_column(String(500))  # Audio file path
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    source_lang: Mapped[str] = mapped_column(String(10), default="zh")
    target_lang: Mapped[str] = mapped_column(String(10), default="en")
    status: Mapped[str] = mapped_column(
        String(50), default="processing"
    )  # processing, completed, failed
    source_type: Mapped[str] = mapped_column(String(20), default="realtime")  # realtime, upload

    # Audio storage - PostgreSQL Large Object OID or SQLite blob_id
    audio_oid: Mapped[int | None] = mapped_column(nullable=True)  # PostgreSQL Large Object OID
    audio_blob_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # SQLite blob ID
    audio_size: Mapped[int | None] = mapped_column(nullable=True)  # Size in bytes
    audio_format: Mapped[str] = mapped_column(String(10), default="opus")  # opus, wav, mp3

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="recordings")
    folder: Mapped[Optional["Folder"]] = relationship("Folder", back_populates="recordings")
    transcript: Mapped[Optional["Transcript"]] = relationship(
        "Transcript",
        back_populates="recording",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    translation: Mapped[Optional["Translation"]] = relationship(
        "Translation",
        back_populates="recording",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    ai_summary: Mapped[Optional["AISummary"]] = relationship(
        "AISummary",
        back_populates="recording",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary="recording_tags", back_populates="recordings", lazy="selectin"
    )


class Transcript(Base):
    """Transcript (STT result) table"""

    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    recording_id: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    # Segments: [{"start": 0.5, "end": 3.2, "text": "..."}]
    segments: Mapped[dict] = mapped_column(JSON, default=list)
    full_text: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(10), default="zh")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    recording: Mapped["Recording"] = relationship("Recording", back_populates="transcript")


class Translation(Base):
    """Translation table"""

    __tablename__ = "translations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    recording_id: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    # Segments: [{"start": 0.5, "end": 3.2, "text": "..."}]
    segments: Mapped[dict] = mapped_column(JSON, default=list)
    full_text: Mapped[str | None] = mapped_column(Text)
    target_lang: Mapped[str] = mapped_column(String(10), default="en")
    llm_model: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    recording: Mapped["Recording"] = relationship("Recording", back_populates="translation")


class AISummary(Base):
    """AI Summary table"""

    __tablename__ = "ai_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    recording_id: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    summary: Mapped[str | None] = mapped_column(Text)
    key_points: Mapped[dict] = mapped_column(JSON, default=list)  # ["point1", "point2"]
    action_items: Mapped[dict] = mapped_column(JSON, default=list)  # ["todo1", "todo2"]
    auto_tags: Mapped[dict] = mapped_column(JSON, default=list)  # ["工作", "会议"]
    chapters: Mapped[dict] = mapped_column(
        JSON, default=list
    )  # [{"timestamp": 0, "title": "..."}, ...]
    llm_model: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    recording: Mapped["Recording"] = relationship("Recording", back_populates="ai_summary")


class Tag(Base):
    """Tag table"""

    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#3b82f6")  # Blue by default

    # Relationships
    recordings: Mapped[list["Recording"]] = relationship(
        "Recording", secondary="recording_tags", back_populates="tags"
    )


class RecordingTag(Base):
    """Recording-Tag association table"""

    __tablename__ = "recording_tags"

    recording_id: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("recordings.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )


class ShareLink(Base):
    """Share link for public access to recordings"""

    __tablename__ = "share_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    recording_id: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Unique token for the share link
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    # When the link expires
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Maximum number of views (None = unlimited)
    max_views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Current view count
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    # Whether to include audio in the shared content
    include_audio: Mapped[bool] = mapped_column(default=True)
    # Whether to include translation
    include_translation: Mapped[bool] = mapped_column(default=True)
    # Whether to include AI summary
    include_summary: Mapped[bool] = mapped_column(default=True)
    # Optional password protection (hashed)
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    # Creator
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    recording: Mapped["Recording"] = relationship("Recording")
    creator: Mapped["User"] = relationship("User")

    def is_valid(self) -> bool:
        """Check if the share link is still valid"""
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        if self.max_views is not None and self.view_count >= self.max_views:
            return False
        return True
