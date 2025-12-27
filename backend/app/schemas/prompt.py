from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PromptTemplateBase(BaseModel):
    name: str = Field(..., max_length=100)
    template_type: str = Field(..., max_length=20)  # translation, summary, etc.
    content: str
    is_active: bool = False


class PromptTemplateCreate(PromptTemplateBase):
    pass


class PromptTemplateUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    template_type: str | None = Field(None, max_length=20)
    content: str | None = None
    is_active: bool | None = None


class PromptTemplateResponse(PromptTemplateBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
