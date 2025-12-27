"""
STT Provider Registry
供应商能力注册表 - 定义每个 STT 供应商的协议类型和 UI 特性
"""

from enum import Enum
from typing import TypedDict


class STTProtocol(str, Enum):
    """STT 协议类型"""

    HTTP_BATCH = "http_batch"  # 伪流式 (HTTP REST API)
    WEBSOCKET_STREAM = "ws_stream"  # 真流式 (WebSocket)


class STTModel(TypedDict):
    """STT 模型定义"""

    id: str
    name: str


class STTProviderConfig(TypedDict):
    """STT 供应商配置"""

    protocol: STTProtocol
    label: str
    models: list[STTModel]
    default_model: str
    ui_features: list[str]
    # Optional: WebSocket endpoint for streaming providers
    ws_endpoint: str | None


# ============================================================
# STT 供应商注册表 (The Single Source of Truth)
# ============================================================
STT_REGISTRY: dict[str, STTProviderConfig] = {
    # === 伪流式家族 (HTTP Batch) ===
    "Groq": {
        "protocol": STTProtocol.HTTP_BATCH,
        "label": "Groq (High Speed)",
        "models": [
            {"id": "whisper-large-v3-turbo", "name": "Whisper V3 Turbo (推荐)"},
            {"id": "whisper-large-v3", "name": "Whisper V3 (高精度)"},
            {"id": "distil-whisper-large-v3-en", "name": "Distil-Whisper (仅英文)"},
        ],
        "default_model": "whisper-large-v3-turbo",
        "ui_features": ["vad_threshold", "buffer_duration"],
        "ws_endpoint": None,
    },
    "OpenAI": {
        "protocol": STTProtocol.HTTP_BATCH,
        "label": "OpenAI Whisper",
        "models": [
            {"id": "whisper-1", "name": "Whisper-1"},
        ],
        "default_model": "whisper-1",
        "ui_features": ["vad_threshold", "buffer_duration"],
        "ws_endpoint": None,
    },
    # === 真流式家族 (WebSocket Stream) ===
    "Deepgram": {
        "protocol": STTProtocol.WEBSOCKET_STREAM,
        "label": "Deepgram (实时流式)",
        "models": [
            # Nova 系列 (支持 Diarization) - Recommended first
            {"id": "nova-3-general", "name": "Nova-3 General"},
            # Flux (需要 v2 endpoint, 仅英文)
            {"id": "flux-general-en", "name": "Flux (英文)", "endpoint": "v2"},
            {"id": "nova-2-general", "name": "Nova-2 General"},
        ],
        "default_model": "nova-3-general",
        "ui_features": ["diarization", "smart_format", "interim_results"],
        "ws_endpoint": "wss://api.deepgram.com/v1/listen",
        "ws_endpoint_v2": "wss://api.deepgram.com/v2/listen",  # for Flux
    },
    "Azure": {
        "protocol": STTProtocol.WEBSOCKET_STREAM,
        "label": "Azure Speech Service",
        "models": [
            {"id": "default", "name": "Azure Default"},
        ],
        "default_model": "default",
        "ui_features": ["diarization"],
        "ws_endpoint": None,  # Azure uses region-specific endpoints
    },
}


# 构建大小写不敏感的查找映射
_PROVIDER_LOOKUP = {k.lower(): k for k in STT_REGISTRY.keys()}


def get_provider_config(provider_name: str) -> STTProviderConfig | None:
    """获取供应商配置 (大小写不敏感)"""
    # 先尝试精确匹配
    if provider_name in STT_REGISTRY:
        return STT_REGISTRY[provider_name]
    # 再尝试大小写不敏感匹配
    canonical_name = _PROVIDER_LOOKUP.get(provider_name.lower())
    return STT_REGISTRY.get(canonical_name) if canonical_name else None


def get_provider_protocol(provider_name: str) -> STTProtocol | None:
    """获取供应商协议类型"""
    config = get_provider_config(provider_name)
    return config["protocol"] if config else None


def is_streaming_provider(provider_name: str) -> bool:
    """判断供应商是否支持真流式"""
    protocol = get_provider_protocol(provider_name)
    return protocol == STTProtocol.WEBSOCKET_STREAM


def get_all_providers() -> list[str]:
    """获取所有供应商名称"""
    return list(STT_REGISTRY.keys())


def get_provider_models(provider_name: str) -> list[STTModel]:
    """获取供应商支持的模型列表"""
    config = get_provider_config(provider_name)
    return config["models"] if config else []
