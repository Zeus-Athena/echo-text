"""
Tests for core/logging.py
日志配置测试
"""

import json
from unittest.mock import MagicMock, patch


class TestLoggingConfiguration:
    """日志配置测试"""

    def test_setup_logging_development(self):
        """测试开发环境日志配置"""
        with patch("app.core.logging.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "development"
            mock_settings.LOG_LEVEL = "DEBUG"

            from app.core.logging import setup_logging

            # 应该不报错
            setup_logging()

    def test_setup_logging_production(self):
        """测试生产环境日志配置"""
        with patch("app.core.logging.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "production"
            mock_settings.LOG_LEVEL = "INFO"

            from app.core.logging import setup_logging

            # 应该不报错
            setup_logging()

    def test_json_serializer_basic(self):
        """测试 JSON 序列化基本功能"""
        from datetime import datetime

        from app.core.logging import json_serializer

        mock_record = {
            "time": datetime(2024, 1, 1, 12, 0, 0, 123456),
            "level": MagicMock(name="INFO"),
            "message": "Test message",
            "name": "test_module",
            "function": "test_func",
            "line": 42,
            "extra": {},
            "exception": None,
        }
        mock_record["level"].name = "INFO"

        result = json_serializer(mock_record)
        parsed = json.loads(result)

        assert parsed["message"] == "Test message"
        assert parsed["level"] == "INFO"
        assert parsed["module"] == "test_module"
        assert parsed["function"] == "test_func"
        assert parsed["line"] == 42

    def test_json_serializer_with_extra(self):
        """测试带额外字段的 JSON 序列化"""
        from datetime import datetime

        from app.core.logging import json_serializer

        mock_record = {
            "time": datetime(2024, 1, 1, 12, 0, 0),
            "level": MagicMock(name="INFO"),
            "message": "Test",
            "name": "test",
            "function": "test",
            "line": 1,
            "extra": {"user_id": "123", "action": "login", "_internal": "skip"},
            "exception": None,
        }
        mock_record["level"].name = "INFO"

        result = json_serializer(mock_record)
        parsed = json.loads(result)

        assert "extra" in parsed
        assert parsed["extra"]["user_id"] == "123"
        assert parsed["extra"]["action"] == "login"
        assert "_internal" not in parsed["extra"]  # 内部字段应被过滤

    def test_json_serializer_with_exception(self):
        """测试带异常信息的 JSON 序列化"""
        from datetime import datetime

        from app.core.logging import json_serializer

        mock_traceback = MagicMock()
        mock_traceback.format.return_value = ["Traceback...\n", "Error line\n"]

        mock_exception = MagicMock()
        mock_exception.type = ValueError
        mock_exception.value = ValueError("test error")
        mock_exception.traceback = mock_traceback

        mock_record = {
            "time": datetime(2024, 1, 1, 12, 0, 0),
            "level": MagicMock(name="ERROR"),
            "message": "Error occurred",
            "name": "test",
            "function": "test",
            "line": 1,
            "extra": {},
            "exception": mock_exception,
        }
        mock_record["level"].name = "ERROR"

        result = json_serializer(mock_record)
        parsed = json.loads(result)

        assert "exception" in parsed
        assert parsed["exception"]["type"] == "ValueError"


class TestLogHelpers:
    """日志辅助函数测试"""

    def test_get_logger(self):
        """测试获取带模块名的 logger"""
        from app.core.logging import get_logger

        log = get_logger("test_module")
        assert log is not None

    def test_log_request(self):
        """测试请求日志记录"""
        from app.core.logging import log_request

        # 应该不报错
        log_request(
            method="GET",
            path="/api/v1/users",
            status_code=200,
            duration_ms=45.6,
            user_id="123",
        )

    def test_log_ws_event(self):
        """测试 WebSocket 事件日志"""
        from app.core.logging import log_ws_event

        # 应该不报错
        log_ws_event(event="connect", client_id="client_123", details={"recording_id": "456"})

    def test_log_external_call_success(self):
        """测试外部调用日志（成功）"""
        from app.core.logging import log_external_call

        # 应该不报错
        log_external_call(
            service="stt",
            provider="groq",
            duration_ms=234.5,
            success=True,
        )

    def test_log_external_call_failure(self):
        """测试外部调用日志（失败）"""
        from app.core.logging import log_external_call

        # 应该不报错
        log_external_call(
            service="llm",
            provider="openai",
            duration_ms=1000.0,
            success=False,
            error="Rate limit exceeded",
        )


class TestLoggingFormats:
    """日志格式测试"""

    def test_colored_format_defined(self):
        """测试彩色格式定义"""
        from app.core.logging import COLORED_FORMAT

        assert "{time:" in COLORED_FORMAT
        assert "{level" in COLORED_FORMAT
        assert "{message}" in COLORED_FORMAT

    def test_plain_format_defined(self):
        """测试纯文本格式定义"""
        from app.core.logging import PLAIN_FORMAT

        assert "{time:" in PLAIN_FORMAT
        assert "{level" in PLAIN_FORMAT
        assert "{message}" in PLAIN_FORMAT
        # 纯文本格式不应包含颜色标签
        assert "<green>" not in PLAIN_FORMAT
