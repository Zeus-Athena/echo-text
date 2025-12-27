"""
Custom Exceptions
应用级自定义异常类型

使用具体异常类型替代字符串匹配，提高错误处理的可靠性和可维护性
"""

from __future__ import annotations

from typing import Any


class EchoTextError(Exception):
    """应用基础异常"""

    def __init__(self, message: str, details: Any = None):
        self.message = message
        self.details = details
        super().__init__(message)


# ========== 认证相关异常 ==========


class AuthenticationError(EchoTextError):
    """认证失败异常"""

    pass


class InvalidTokenError(AuthenticationError):
    """无效 Token"""

    pass


class TokenExpiredError(AuthenticationError):
    """Token 已过期"""

    pass


class PermissionDeniedError(EchoTextError):
    """权限不足"""

    pass


# ========== 资源相关异常 ==========


class ResourceNotFoundError(EchoTextError):
    """资源未找到"""

    def __init__(self, resource_type: str, resource_id: str | None = None):
        message = f"{resource_type} not found"
        if resource_id:
            message = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(message)
        self.resource_type = resource_type
        self.resource_id = resource_id


class ResourceExistsError(EchoTextError):
    """资源已存在"""

    def __init__(self, resource_type: str, identifier: str):
        message = f"{resource_type} with identifier '{identifier}' already exists"
        super().__init__(message)
        self.resource_type = resource_type
        self.identifier = identifier


# ========== 外部服务异常 ==========


class ExternalServiceError(EchoTextError):
    """外部服务调用异常基类"""

    def __init__(self, service: str, message: str, details: Any = None):
        super().__init__(f"{service} error: {message}", details)
        self.service = service


class STTServiceError(ExternalServiceError):
    """STT 服务异常"""

    def __init__(self, message: str, provider: str | None = None, details: Any = None):
        super().__init__("STT", message, details)
        self.provider = provider


class LLMServiceError(ExternalServiceError):
    """LLM 服务异常"""

    def __init__(self, message: str, provider: str | None = None, details: Any = None):
        super().__init__("LLM", message, details)
        self.provider = provider


class TTSServiceError(ExternalServiceError):
    """TTS 服务异常"""

    def __init__(self, message: str, provider: str | None = None, details: Any = None):
        super().__init__("TTS", message, details)
        self.provider = provider


class DiarizationServiceError(ExternalServiceError):
    """说话人分离服务异常"""

    def __init__(self, message: str, provider: str | None = None, details: Any = None):
        super().__init__("Diarization", message, details)
        self.provider = provider


# ========== 音频处理异常 ==========


class AudioProcessingError(EchoTextError):
    """音频处理异常"""

    pass


class AudioConversionError(AudioProcessingError):
    """音频转码异常"""

    pass


class AudioTooShortError(AudioProcessingError):
    """音频过短"""

    def __init__(self, duration: float, min_duration: float = 0.5):
        super().__init__(f"Audio too short: {duration:.2f}s (minimum: {min_duration:.2f}s)")
        self.duration = duration
        self.min_duration = min_duration


# ========== WebSocket 异常 ==========


class WebSocketError(EchoTextError):
    """WebSocket 异常基类"""

    pass


class WebSocketConnectionClosed(WebSocketError):
    """WebSocket 连接已关闭"""

    def __init__(self, code: int | None = None, reason: str | None = None):
        message = "WebSocket connection closed"
        if code:
            message += f" (code: {code})"
        if reason:
            message += f": {reason}"
        super().__init__(message)
        self.code = code
        self.reason = reason


class WebSocketSendError(WebSocketError):
    """WebSocket 发送失败"""

    pass


# ========== 配置异常 ==========


class ConfigurationError(EchoTextError):
    """配置错误"""

    pass


class MissingConfigError(ConfigurationError):
    """缺少必需配置"""

    def __init__(self, config_key: str):
        super().__init__(f"Missing required configuration: {config_key}")
        self.config_key = config_key


class InvalidConfigError(ConfigurationError):
    """无效配置值"""

    def __init__(self, config_key: str, value: Any, reason: str | None = None):
        message = f"Invalid configuration value for '{config_key}': {value}"
        if reason:
            message += f" ({reason})"
        super().__init__(message)
        self.config_key = config_key
        self.value = value


# ========== 限流异常 ==========


class RateLimitError(EchoTextError):
    """触发限流"""

    def __init__(self, service: str, limit: int | None = None, retry_after: int | None = None):
        message = f"Rate limit exceeded for {service}"
        if limit:
            message += f" (limit: {limit})"
        super().__init__(message)
        self.service = service
        self.limit = limit
        self.retry_after = retry_after


# ========== 验证异常 ==========


class ValidationError(EchoTextError):
    """验证错误"""

    def __init__(self, field: str, message: str):
        super().__init__(f"Validation error for '{field}': {message}")
        self.field = field
