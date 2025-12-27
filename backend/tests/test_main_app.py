"""
Main App Tests
测试 main.py 入口点和核心模块
"""

import pytest


class TestAppVersion:
    """测试版本信息"""

    def test_version_exists(self):
        """测试版本信息存在"""
        from app.__version__ import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0


class TestExceptionClasses:
    """测试自定义异常类"""

    def test_echotext_error_base(self):
        """测试基础异常类"""
        from app.core.exceptions import EchoTextError

        exc = EchoTextError("test message")
        assert exc.message == "test message"
        assert exc.details is None

        exc_with_details = EchoTextError("test", details={"key": "value"})
        assert exc_with_details.details == {"key": "value"}

    def test_authentication_errors(self):
        """测试认证异常类"""
        from app.core.exceptions import (
            AuthenticationError,
            InvalidTokenError,
            TokenExpiredError,
        )

        assert AuthenticationError("test").message == "test"
        assert InvalidTokenError("test").message == "test"
        assert TokenExpiredError("test").message == "test"

    def test_permission_denied_error(self):
        """测试权限异常"""
        from app.core.exceptions import PermissionDeniedError

        exc = PermissionDeniedError("Access denied")
        assert exc.message == "Access denied"

    def test_resource_not_found_error(self):
        """测试资源未找到异常"""
        from app.core.exceptions import ResourceNotFoundError

        exc = ResourceNotFoundError("Recording")
        assert "Recording not found" in exc.message

        exc_with_id = ResourceNotFoundError("Recording", "123")
        assert "123" in exc_with_id.message
        assert exc_with_id.resource_type == "Recording"
        assert exc_with_id.resource_id == "123"

    def test_resource_exists_error(self):
        """测试资源已存在异常"""
        from app.core.exceptions import ResourceExistsError

        exc = ResourceExistsError("User", "test@example.com")
        assert "already exists" in exc.message
        assert exc.resource_type == "User"
        assert exc.identifier == "test@example.com"

    def test_external_service_errors(self):
        """测试外部服务异常类"""
        from app.core.exceptions import (
            DiarizationServiceError,
            ExternalServiceError,
            LLMServiceError,
            STTServiceError,
            TTSServiceError,
        )

        exc = ExternalServiceError("API", "failed")
        assert "API" in exc.message

        stt_exc = STTServiceError("transcription failed", provider="groq")
        assert "STT" in stt_exc.message
        assert stt_exc.provider == "groq"

        llm_exc = LLMServiceError("translation failed", provider="openai")
        assert "LLM" in llm_exc.message

        tts_exc = TTSServiceError("synthesis failed")
        assert "TTS" in tts_exc.message

        dia_exc = DiarizationServiceError("diarization failed")
        assert "Diarization" in dia_exc.message

    def test_audio_processing_errors(self):
        """测试音频处理异常类"""
        from app.core.exceptions import (
            AudioConversionError,
            AudioProcessingError,
            AudioTooShortError,
        )

        assert AudioProcessingError("error").message == "error"
        assert AudioConversionError("conversion failed").message == "conversion failed"

        short_exc = AudioTooShortError(0.3, min_duration=0.5)
        assert "0.30" in short_exc.message
        assert short_exc.duration == 0.3
        assert short_exc.min_duration == 0.5

    def test_websocket_errors(self):
        """测试 WebSocket 异常类"""
        from app.core.exceptions import (
            WebSocketConnectionClosed,
            WebSocketError,
            WebSocketSendError,
        )

        assert WebSocketError("error").message == "error"

        closed_exc = WebSocketConnectionClosed(code=1000, reason="normal")
        assert "1000" in closed_exc.message
        assert "normal" in closed_exc.message

        assert WebSocketSendError("send failed").message == "send failed"

    def test_configuration_errors(self):
        """测试配置异常类"""
        from app.core.exceptions import (
            ConfigurationError,
            InvalidConfigError,
            MissingConfigError,
        )

        assert ConfigurationError("error").message == "error"

        missing_exc = MissingConfigError("API_KEY")
        assert "API_KEY" in missing_exc.message
        assert missing_exc.config_key == "API_KEY"

        invalid_exc = InvalidConfigError("PORT", "abc", reason="must be integer")
        assert "PORT" in invalid_exc.message
        assert "abc" in invalid_exc.message
        assert invalid_exc.value == "abc"

    def test_rate_limit_error(self):
        """测试限流异常"""
        from app.core.exceptions import RateLimitError

        exc = RateLimitError("API", limit=100, retry_after=60)
        assert "API" in exc.message
        assert exc.limit == 100
        assert exc.retry_after == 60

    def test_validation_error(self):
        """测试验证异常"""
        from app.core.exceptions import ValidationError

        exc = ValidationError("email", "invalid format")
        assert "email" in exc.message
        assert exc.field == "email"


class TestDatabaseModule:
    """测试数据库模块"""

    def test_get_db_returns_async_generator(self):
        """测试 get_db 返回异步生成器"""
        from app.core.database import get_db

        gen = get_db()
        assert hasattr(gen, "__anext__")


class TestConfigModule:
    """测试配置模块"""

    def test_settings_loaded(self):
        """测试设置已加载"""
        from app.core.config import settings

        assert settings is not None
        assert hasattr(settings, "DATABASE_URL")
        assert hasattr(settings, "SECRET_KEY")
        assert hasattr(settings, "ALGORITHM")

    def test_settings_algorithm_default(self):
        """测试算法默认值"""
        from app.core.config import settings

        assert settings.ALGORITHM == "HS256"


class TestRootEndpoint:
    """测试根端点"""

    @pytest.mark.asyncio
    async def test_root_returns_welcome(self):
        """测试根节点返回欢迎信息"""
        from app.main import root

        result = await root()

        assert "message" in result
        assert "Welcome" in result["message"]
        assert "version" in result
