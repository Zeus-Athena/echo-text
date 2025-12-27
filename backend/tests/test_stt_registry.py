"""
Tests for STT Registry
测试供应商注册表功能
"""

from app.core.stt_registry import (
    STT_REGISTRY,
    STTProtocol,
    get_all_providers,
    get_provider_config,
    get_provider_models,
    get_provider_protocol,
    is_streaming_provider,
)


class TestSTTRegistry:
    """测试 STT 注册表"""

    def test_registry_has_groq(self):
        """Groq 应该在注册表中"""
        assert "Groq" in STT_REGISTRY

    def test_registry_has_deepgram(self):
        """Deepgram 应该在注册表中"""
        assert "Deepgram" in STT_REGISTRY

    def test_groq_is_http_batch(self):
        """Groq 应该是 HTTP_BATCH 协议"""
        config = get_provider_config("Groq")
        assert config is not None
        assert config["protocol"] == STTProtocol.HTTP_BATCH

    def test_deepgram_is_websocket_stream(self):
        """Deepgram 应该是 WEBSOCKET_STREAM 协议"""
        config = get_provider_config("Deepgram")
        assert config is not None
        assert config["protocol"] == STTProtocol.WEBSOCKET_STREAM

    def test_get_provider_protocol_groq(self):
        """get_provider_protocol 应该返回正确的协议"""
        protocol = get_provider_protocol("Groq")
        assert protocol == STTProtocol.HTTP_BATCH

    def test_get_provider_protocol_unknown(self):
        """未知供应商应该返回 None"""
        protocol = get_provider_protocol("UnknownProvider")
        assert protocol is None

    def test_is_streaming_provider_deepgram(self):
        """Deepgram 应该是流式供应商"""
        assert is_streaming_provider("Deepgram") is True

    def test_is_streaming_provider_groq(self):
        """Groq 不应该是流式供应商"""
        assert is_streaming_provider("Groq") is False

    def test_get_all_providers(self):
        """应该返回所有供应商名称"""
        providers = get_all_providers()
        assert "Groq" in providers
        assert "Deepgram" in providers
        assert len(providers) >= 2

    def test_get_provider_models_groq(self):
        """应该返回 Groq 的模型列表"""
        models = get_provider_models("Groq")
        assert len(models) > 0
        model_ids = [m["id"] for m in models]
        assert "whisper-large-v3-turbo" in model_ids

    def test_get_provider_models_unknown(self):
        """未知供应商应该返回空列表"""
        models = get_provider_models("UnknownProvider")
        assert models == []

    def test_provider_has_ui_features(self):
        """供应商应该有 UI 特性定义"""
        groq_config = get_provider_config("Groq")
        assert "ui_features" in groq_config
        assert "vad_threshold" in groq_config["ui_features"]

        deepgram_config = get_provider_config("Deepgram")
        assert "ui_features" in deepgram_config
        assert "diarization" in deepgram_config["ui_features"]

    def test_provider_has_default_model(self):
        """供应商应该有默认模型"""
        for provider_name in get_all_providers():
            config = get_provider_config(provider_name)
            assert "default_model" in config
            assert config["default_model"] is not None
