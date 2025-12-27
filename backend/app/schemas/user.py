from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# ========== Auth Schemas ==========


class UserRegister(BaseModel):
    """User registration request"""

    email: EmailStr
    username: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6, max_length=100)


class UserLogin(BaseModel):
    """User login request - login by username"""

    username: str
    password: str


class AdminCreateUser(BaseModel):
    """Admin create user request"""

    email: EmailStr
    username: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6, max_length=100)
    can_use_admin_key: bool = False


class Token(BaseModel):
    """Token response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Token refresh request"""

    refresh_token: str


# ========== User Schemas ==========


class UserBase(BaseModel):
    """Base user schema"""

    email: EmailStr
    username: str


class UserResponse(UserBase):
    """User response"""

    id: UUID
    role: str
    is_active: bool
    can_use_admin_key: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User update request"""

    username: str | None = None
    email: EmailStr | None = None


class PasswordChange(BaseModel):
    """Password change request"""

    current_password: str
    new_password: str = Field(min_length=6, max_length=100)


class AdminUpdateUser(BaseModel):
    """Admin update user request"""

    username: str | None = None
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=6, max_length=100)
    can_use_admin_key: bool | None = None


# ========== User Config Schemas ==========


class LLMConfig(BaseModel):
    """LLM configuration"""

    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    keys: dict[str, str | None] | None = None


class STTConfig(BaseModel):
    """STT configuration"""

    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    keys: dict[str, str | None] | None = None


class TTSConfig(BaseModel):
    """TTS configuration"""

    provider: str = "edge"
    api_key: str | None = None
    base_url: str | None = None
    voice: str = "zh-CN-XiaoxiaoNeural"


class DictConfig(BaseModel):
    """Dictionary configuration"""

    provider: str = "llm"
    api_key: str | None = None


class PreferencesConfig(BaseModel):
    """User preferences"""

    theme: str = "system"
    default_source_lang: str = "zh"
    default_target_lang: str = "en"


class RecordingConfig(BaseModel):
    """Recording configuration"""

    audio_buffer_duration: int = 6
    silence_threshold: int = 30
    silence_mode: str = "manual"  # "manual" | "adaptive"
    silence_prefer_source: str = "current"  # "current" | "auto"
    silence_threshold_source: str = "default"  # "default" | "manual" | "manual_detect" | "auto"
    translation_mode: int = 0
    segment_soft_threshold: int = 50
    segment_hard_threshold: int = 100


class UserConfigResponse(BaseModel):
    """Full user config response"""

    llm: LLMConfig
    stt: STTConfig
    tts: TTSConfig
    dict: DictConfig
    preferences: PreferencesConfig
    recording: RecordingConfig
    using_admin_key: bool = False  # Whether using admin's API keys

    class Config:
        from_attributes = True


class UserConfigUpdate(BaseModel):
    """User config update request"""

    llm: LLMConfig | None = None
    stt: STTConfig | None = None
    tts: TTSConfig | None = None
    dict: DictConfig | None = None
    preferences: PreferencesConfig | None = None
    recording: RecordingConfig | None = None


# ========== Config Test Schemas ==========


class ConfigTestRequest(BaseModel):
    """Config test request"""

    provider: str
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None


class ConfigTestResponse(BaseModel):
    """Config test response"""

    success: bool
    message: str
    provider: str
    latency_ms: int | None = None
