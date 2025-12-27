"""
Prompt Template Model
自定义提示词模板
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import UUID


class PromptTemplate(Base):
    """Custom prompt templates for LLM tasks"""

    __tablename__ = "prompt_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Template name (e.g., "Academic Translation", "Casual Chat")
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Template type: 'translation', 'summary', 'dictionary'
    template_type: Mapped[str] = mapped_column(String(20), default="translation")

    # Content with mustache-style variables, e.g., {{text}}, {{source_lang}}
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Is this the default template for this type?
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
