"""
ARQ Redis Settings
ARQ 连接配置
"""

from arq.connections import RedisSettings

from app.core.config import settings


def get_redis_settings() -> RedisSettings:
    """Get Redis settings for ARQ"""
    return RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
    )


REDIS_SETTINGS = get_redis_settings()
