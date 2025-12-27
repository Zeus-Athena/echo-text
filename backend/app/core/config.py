"""
Application Configuration
从环境变量加载配置
"""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Environment
    ENVIRONMENT: str = "development"

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Ensure critical settings are configured in production"""
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "your-super-secret-key-change-in-production":
                raise ValueError(
                    "SECRET_KEY must be changed in production! "
                    "Set a secure random key via environment variable."
                )
            if "sqlite" in self.DATABASE_URL:
                raise ValueError(
                    "Production must use PostgreSQL! Please set DATABASE_URL environment variable."
                )
        return self

    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"  # DEBUG, INFO, WARNING, ERROR

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"

    # Database (SQLite for development, PostgreSQL for production)
    DATABASE_URL: str = "sqlite+aiosqlite:///./echotext.db"

    # Redis (optional)
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # JWT
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "https://trans.227337.xyz",  # Production
    ]

    # File Storage (S3 compatible)
    S3_ENDPOINT: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "echotext"

    # Default AI Providers (can be overridden per user)
    DEFAULT_LLM_PROVIDER: str = "SiliconFlow"
    DEFAULT_LLM_BASE_URL: str = "https://api.siliconflow.cn/v1"
    DEFAULT_LLM_MODEL: str = "deepseek-ai/DeepSeek-V3"

    DEFAULT_STT_PROVIDER: str = "Groq"
    DEFAULT_STT_BASE_URL: str = "https://api.groq.com/openai/v1"
    DEFAULT_STT_MODEL: str = "whisper-large-v3-turbo"

    DEFAULT_TTS_PROVIDER: str = "edge"
    DEFAULT_TTS_VOICE: str = "zh-CN-XiaoxiaoNeural"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
