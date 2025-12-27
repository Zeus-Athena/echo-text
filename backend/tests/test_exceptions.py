"""
Tests for core/exceptions.py
自定义异常测试
"""

from app.core.exceptions import (
    AudioConversionError,
    AudioProcessingError,
    AudioTooShortError,
    AuthenticationError,
    ConfigurationError,
    DiarizationServiceError,
    EchoTextError,
    ExternalServiceError,
    InvalidConfigError,
    InvalidTokenError,
    LLMServiceError,
    MissingConfigError,
    PermissionDeniedError,
    RateLimitError,
    ResourceExistsError,
    ResourceNotFoundError,
    STTServiceError,
    TokenExpiredError,
    TTSServiceError,
    ValidationError,
    WebSocketConnectionClosed,
    WebSocketError,
    WebSocketSendError,
)


class TestEchoTextError:
    """基础异常测试"""

    def test_basic_creation(self):
        """测试基本创建"""
        err = EchoTextError("Test error")
        assert err.message == "Test error"
        assert str(err) == "Test error"

    def test_with_details(self):
        """测试带详情"""
        err = EchoTextError("Test error", details={"key": "value"})
        assert err.details == {"key": "value"}


class TestAuthenticationErrors:
    """认证异常测试"""

    def test_authentication_error(self):
        err = AuthenticationError("Auth failed")
        assert isinstance(err, EchoTextError)
        assert err.message == "Auth failed"

    def test_invalid_token_error(self):
        err = InvalidTokenError("Invalid token")
        assert isinstance(err, AuthenticationError)

    def test_token_expired_error(self):
        err = TokenExpiredError("Token expired")
        assert isinstance(err, AuthenticationError)

    def test_permission_denied_error(self):
        err = PermissionDeniedError("No permission")
        assert isinstance(err, EchoTextError)


class TestResourceErrors:
    """资源异常测试"""

    def test_resource_not_found(self):
        err = ResourceNotFoundError("Recording")
        assert "Recording" in err.message
        assert err.resource_type == "Recording"
        assert err.resource_id is None

    def test_resource_not_found_with_id(self):
        err = ResourceNotFoundError("Recording", "123")
        assert "123" in err.message
        assert err.resource_id == "123"

    def test_resource_exists(self):
        err = ResourceExistsError("User", "email@test.com")
        assert "User" in err.message
        assert "email@test.com" in err.message
        assert err.resource_type == "User"
        assert err.identifier == "email@test.com"


class TestExternalServiceErrors:
    """外部服务异常测试"""

    def test_external_service_error(self):
        err = ExternalServiceError("API", "Connection failed")
        assert err.service == "API"
        assert "API" in err.message

    def test_stt_service_error(self):
        err = STTServiceError("Transcription failed", provider="groq")
        assert err.service == "STT"
        assert err.provider == "groq"

    def test_llm_service_error(self):
        err = LLMServiceError("Translation failed", provider="openai")
        assert err.service == "LLM"
        assert err.provider == "openai"

    def test_tts_service_error(self):
        err = TTSServiceError("Speech synthesis failed", provider="edge")
        assert err.service == "TTS"
        assert err.provider == "edge"

    def test_diarization_service_error(self):
        err = DiarizationServiceError("Diarization failed", provider="assemblyai")
        assert err.service == "Diarization"
        assert err.provider == "assemblyai"


class TestAudioProcessingErrors:
    """音频处理异常测试"""

    def test_audio_processing_error(self):
        err = AudioProcessingError("Processing failed")
        assert isinstance(err, EchoTextError)

    def test_audio_conversion_error(self):
        err = AudioConversionError("Conversion failed")
        assert isinstance(err, AudioProcessingError)

    def test_audio_too_short_error(self):
        err = AudioTooShortError(duration=0.3, min_duration=0.5)
        assert err.duration == 0.3
        assert err.min_duration == 0.5
        assert "0.30s" in err.message
        assert "0.50s" in err.message


class TestWebSocketErrors:
    """WebSocket 异常测试"""

    def test_websocket_error(self):
        err = WebSocketError("WS error")
        assert isinstance(err, EchoTextError)

    def test_websocket_connection_closed(self):
        err = WebSocketConnectionClosed()
        assert "closed" in err.message.lower()
        assert err.code is None
        assert err.reason is None

    def test_websocket_connection_closed_with_code(self):
        err = WebSocketConnectionClosed(code=1000, reason="Normal closure")
        assert "1000" in err.message
        assert "Normal closure" in err.message
        assert err.code == 1000
        assert err.reason == "Normal closure"

    def test_websocket_send_error(self):
        err = WebSocketSendError("Failed to send")
        assert isinstance(err, WebSocketError)


class TestConfigurationErrors:
    """配置异常测试"""

    def test_configuration_error(self):
        err = ConfigurationError("Config invalid")
        assert isinstance(err, EchoTextError)

    def test_missing_config_error(self):
        err = MissingConfigError("API_KEY")
        assert err.config_key == "API_KEY"
        assert "API_KEY" in err.message

    def test_invalid_config_error(self):
        err = InvalidConfigError("timeout", -1, "must be positive")
        assert err.config_key == "timeout"
        assert err.value == -1
        assert "must be positive" in err.message


class TestRateLimitError:
    """限流异常测试"""

    def test_rate_limit_error(self):
        err = RateLimitError("groq")
        assert err.service == "groq"
        assert "groq" in err.message

    def test_rate_limit_error_with_details(self):
        err = RateLimitError("openai", limit=60, retry_after=30)
        assert err.limit == 60
        assert err.retry_after == 30
        assert "60" in err.message


class TestValidationError:
    """验证异常测试"""

    def test_validation_error(self):
        err = ValidationError("email", "invalid format")
        assert err.field == "email"
        assert "email" in err.message
        assert "invalid format" in err.message
