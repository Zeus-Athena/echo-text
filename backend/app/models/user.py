"""
User Model
用户数据模型
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UUID


class User(Base):
    """User table"""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user")  # 'user' or 'admin'
    is_active: Mapped[bool] = mapped_column(default=True)
    can_use_admin_key: Mapped[bool] = mapped_column(default=False)  # Allow using admin's API keys
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    config: Mapped[Optional["UserConfig"]] = relationship(
        "UserConfig",
        back_populates="user",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    recordings: Mapped[list["Recording"]] = relationship(
        "Recording", back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )
    folders: Mapped[list["Folder"]] = relationship(
        "Folder", back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )


class UserConfig(Base):
    """User configuration table"""

    __tablename__ = "user_configs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    # LLM Configuration
    llm_provider: Mapped[str | None] = mapped_column(String(100))
    llm_api_key: Mapped[str | None] = mapped_column(Text)  # Deprecated - use provider-specific keys
    llm_base_url: Mapped[str | None] = mapped_column(String(500))
    llm_model: Mapped[str | None] = mapped_column(String(200))

    # LLM Provider-specific API Keys (新增)
    llm_groq_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_siliconflow_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    # STT Configuration
    stt_provider: Mapped[str | None] = mapped_column(String(100))
    stt_api_key: Mapped[str | None] = mapped_column(Text)  # Deprecated - use provider-specific keys
    stt_base_url: Mapped[str | None] = mapped_column(String(500))
    stt_model: Mapped[str | None] = mapped_column(String(200))

    # STT Provider-specific API Keys (新增)
    stt_groq_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    stt_deepgram_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    stt_openai_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    stt_siliconflow_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    # TTS Configuration
    tts_provider: Mapped[str] = mapped_column(String(100), default="edge")
    tts_api_key: Mapped[str | None] = mapped_column(Text)
    tts_base_url: Mapped[str | None] = mapped_column(String(500))
    tts_voice: Mapped[str] = mapped_column(String(200), default="zh-CN-XiaoxiaoNeural")

    # Dictionary Configuration
    dict_provider: Mapped[str] = mapped_column(String(100), default="llm")
    dict_api_key: Mapped[str | None] = mapped_column(Text)

    # Preferences
    theme: Mapped[str] = mapped_column(String(20), default="system")
    default_source_lang: Mapped[str] = mapped_column(String(10), default="zh")
    default_target_lang: Mapped[str] = mapped_column(String(10), default="en")

    # Recording Configuration
    audio_buffer_duration: Mapped[int] = mapped_column(default=6)
    silence_threshold: Mapped[int] = mapped_column(default=30)
    silence_mode: Mapped[str] = mapped_column(String(20), default="manual")  # "manual" | "adaptive"
    silence_prefer_source: Mapped[str] = mapped_column(
        String(20), default="current"
    )  # "current" | "auto"
    silence_threshold_source: Mapped[str] = mapped_column(
        String(20), default="default"
    )  # "default" | "manual" | "manual_detect" | "auto"

    # Translation Mode (for Deepgram streaming)
    # 0 = fast mode (translate every 5 words)
    # 6 = throttle mode (translate at sentence end)
    translation_mode: Mapped[int] = mapped_column(default=0)

    # Segment threshold for UI (new)
    segment_soft_threshold: Mapped[int] = mapped_column(default=50)  # words per card (soft)
    segment_hard_threshold: Mapped[int] = mapped_column(default=100)  # words per card (hard limit)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="config")
