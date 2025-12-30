"""
STT Model Registry
STT 模型能力注册表 - 按模型判断流式类型

功能：
1. 定义模型 -> 流式类型的映射
2. 提供查询接口供 ws_v2.py 和配置 API 使用
"""

from __future__ import annotations

from loguru import logger

# 模型流式类型映射
# key: 模型名称（小写）
# value: "true_streaming" 或 "simulated_streaming"
MODEL_STREAMING_TYPE: dict[str, str] = {
    # Deepgram 真流式模型
    "nova-2": "true_streaming",
    "nova-2-general": "true_streaming",
    "nova-2-meeting": "true_streaming",
    "nova-2-phonecall": "true_streaming",
    "nova-2-finance": "true_streaming",
    "nova-2-conversationalai": "true_streaming",
    "nova-2-voicemail": "true_streaming",
    "nova-2-video": "true_streaming",
    "nova-2-medical": "true_streaming",
    "nova-2-drivethru": "true_streaming",
    "nova-2-automotive": "true_streaming",
    "nova-3": "true_streaming",
    "flux-1-nova": "true_streaming",
    # Deepgram 伪流式模型
    "whisper-large": "simulated_streaming",
    "whisper-medium": "simulated_streaming",
    "whisper-small": "simulated_streaming",
    "whisper-base": "simulated_streaming",
    "whisper-tiny": "simulated_streaming",
    # Groq
    "whisper-large-v3-turbo": "simulated_streaming",
    "whisper-large-v3": "simulated_streaming",
    "distil-whisper-large-v3-en": "simulated_streaming",
    # OpenAI
    "whisper-1": "simulated_streaming",
    # SiliconFlow
    "sensevoice": "simulated_streaming",
    "sensevoice-small": "simulated_streaming",
}

# Provider 默认流式类型（当模型不在映射表中时使用）
PROVIDER_DEFAULT_STREAMING_TYPE: dict[str, str] = {
    "deepgram": "true_streaming",  # Deepgram 默认真流式
    "groq": "simulated_streaming",
    "openai": "simulated_streaming",
    "siliconflow": "simulated_streaming",
}


def get_streaming_type(provider: str, model: str) -> str:
    """
    根据模型判断流式类型
    
    Args:
        provider: STT Provider 名称
        model: STT 模型名称
        
    Returns:
        "true_streaming" 或 "simulated_streaming"
    """
    model_lower = (model or "").lower()
    provider_lower = (provider or "").lower()
    
    # 优先按模型查找
    if model_lower in MODEL_STREAMING_TYPE:
        return MODEL_STREAMING_TYPE[model_lower]
    
    # 模型不在映射表中，按 Provider 默认
    streaming_type = PROVIDER_DEFAULT_STREAMING_TYPE.get(provider_lower, "simulated_streaming")
    
    logger.debug(
        f"Model '{model}' not in registry, using provider default: {streaming_type}"
    )
    
    return streaming_type


def is_true_streaming(provider: str, model: str) -> bool:
    """
    判断模型是否支持真流式
    
    Args:
        provider: STT Provider 名称
        model: STT 模型名称
        
    Returns:
        True 表示真流式，False 表示伪流式
    """
    return get_streaming_type(provider, model) == "true_streaming"
