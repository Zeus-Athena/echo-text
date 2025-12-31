"""
Provider Metadata API
Provider 配置元数据接口 - 统一配置源
"""

from fastapi import APIRouter

from app.schemas.providers import ModelInfo, ProviderInfo, ProvidersMetadataResponse

router = APIRouter(prefix="/config", tags=["Config Metadata"])

# ==================== LLM Providers ====================

LLM_PROVIDERS: list[ProviderInfo] = [
    ProviderInfo(
        id="siliconflow",
        name="SiliconFlow (硅基流动)",
        base_url="https://api.siliconflow.cn/v1",
        help_text="获取 Key: https://cloud.siliconflow.cn",
        models=[
            ModelInfo(
                id="deepseek-ai/DeepSeek-V3",
                name="DeepSeek-V3 (最新)",
                pricing="¥1/M tokens",
                recommended=True,
            ),
            ModelInfo(
                id="Pro/deepseek-ai/DeepSeek-V3",
                name="DeepSeek-V3 Pro",
                pricing="¥2/M tokens",
            ),
            ModelInfo(
                id="deepseek-ai/DeepSeek-R1",
                name="DeepSeek-R1 (推理)",
                pricing="¥4/M tokens",
            ),
            ModelInfo(
                id="deepseek-ai/DeepSeek-V2.5",
                name="DeepSeek-V2.5",
                pricing="¥0.5/M tokens",
            ),
            ModelInfo(
                id="Qwen/Qwen3-30B-A3B-Instruct-2507",
                name="Qwen3-30B-A3B (快速)",
                pricing="¥0.35/M tokens",
            ),
            ModelInfo(
                id="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
                name="DeepSeek-R1-7B (免费)",
                pricing="免费",
            ),
        ],
    ),
    ProviderInfo(
        id="siliconflowglobal",
        name="SiliconFlow Global (国际站)",
        base_url="https://api.siliconflow.com/v1",
        help_text="获取 Key: https://cloud.siliconflow.com",
        models=[
            ModelInfo(
                id="Qwen/Qwen3-30B-A3B-Instruct-2507",
                name="Qwen3-30B-A3B",
                pricing="$0.3/M tokens",
                recommended=True,
            ),
            ModelInfo(
                id="Qwen/Qwen3-Next-80B-A3B-Instruct",
                name="Qwen3-Next-80B-A3B",
                pricing="$1.4/M tokens",
            ),
            ModelInfo(
                id="Qwen/Qwen3-235B-A22B-Instruct-2507",
                name="Qwen3-235B-A22B",
                pricing="$0.6/M tokens",
            ),
        ],
    ),
    ProviderInfo(
        id="groq",
        name="GROQ (免费)",
        base_url="https://api.groq.com/openai/v1",
        help_text="获取 Key: https://console.groq.com",
        models=[
            ModelInfo(
                id="llama-3.3-70b-versatile",
                name="Llama 3.3 70B Versatile",
                pricing="免费",
                recommended=True,
            ),
        ],
    ),
    ProviderInfo(
        id="fireworks",
        name="Fireworks.ai",
        base_url="https://api.fireworks.ai/inference/v1",
        help_text="获取 Key: https://fireworks.ai",
        models=[
            ModelInfo(
                id="accounts/fireworks/models/deepseek-v3p2",
                name="DeepSeek V3.2 (精准)",
                pricing="$0.56/$1.68 /M",
            ),
            ModelInfo(
                id="accounts/fireworks/models/qwen3-235b-a22b",
                name="Qwen3 235B A22B (基础)",
                pricing="$0.22/$0.88 /M",
            ),
            ModelInfo(
                id="accounts/fireworks/models/qwen3-235b-a22b-instruct-2507",
                name="Qwen3 235B Instruct 2507 (推荐)",
                pricing="$0.22/$0.88 /M",
                recommended=True,
            ),
            ModelInfo(
                id="accounts/fireworks/models/qwen3-235b-a22b-thinking-2507",
                name="Qwen3 235B Thinking 2507",
                pricing="$0.22/$0.88 /M",
            ),
            ModelInfo(
                id="accounts/fireworks/models/gpt-oss-120b",
                name="GPT-OSS 120B (便宜)",
                pricing="$0.15/$0.60 /M",
            ),
        ],
    ),
    # Custom provider for user-defined OpenAI-compatible endpoints
    ProviderInfo(
        id="custom",
        name="自定义 (OpenAI Compatible)",
        base_url="",  # User must provide
        help_text="支持任何 OpenAI 兼容接口，如 Ollama、OneAPI、DeepSeek 官方 API 等",
        models=[],  # User must input manually
    ),
]

# ==================== STT Providers ====================

STT_PROVIDERS: list[ProviderInfo] = [
    ProviderInfo(
        id="siliconflow",
        name="SiliconFlow (硅基流动)",
        base_url="https://api.siliconflow.cn/v1",
        help_text="获取 Key: https://cloud.siliconflow.cn",
        models=[
            ModelInfo(
                id="FunAudioLLM/SenseVoiceSmall",
                name="SenseVoice Small",
                pricing="¥0.01/次",
                accuracy="⭐⭐⭐⭐⭐",
                recommended=True,
            ),
            ModelInfo(
                id="TeleAI/TeleSpeechASR",
                name="TeleSpeech ASR",
                pricing="¥0.01/次",
                accuracy="⭐⭐⭐⭐",
            ),
        ],
    ),
    ProviderInfo(
        id="groq",
        name="GROQ (免费)",
        base_url="https://api.groq.com/openai/v1",
        help_text="获取 Key: https://console.groq.com",
        models=[
            ModelInfo(
                id="whisper-large-v3-turbo",
                name="Whisper Large V3 Turbo",
                pricing="免费",
                accuracy="⭐⭐⭐⭐⭐",
                recommended=True,
            ),
            ModelInfo(
                id="whisper-large-v3",
                name="Whisper Large V3",
                pricing="免费",
                accuracy="⭐⭐⭐⭐⭐",
            ),
            ModelInfo(
                id="distil-whisper-large-v3-en",
                name="Distil Whisper (English)",
                pricing="免费",
                accuracy="⭐⭐⭐⭐",
            ),
        ],
    ),
    ProviderInfo(
        id="openai",
        name="OpenAI (付费)",
        base_url="https://api.openai.com/v1",
        help_text="获取 Key: https://platform.openai.com",
        models=[
            ModelInfo(
                id="whisper-1",
                name="Whisper-1",
                pricing="$0.006/分钟",
                accuracy="⭐⭐⭐⭐⭐",
            ),
        ],
    ),
    ProviderInfo(
        id="deepgram",
        name="Deepgram (实时流式)",
        base_url="https://api.deepgram.com/v1",
        help_text="获取 Key: https://console.deepgram.com",
        models=[
            ModelInfo(
                id="nova-3-general",
                name="Nova-3 General",
                pricing="$0.0059/分钟",
                accuracy="⭐⭐⭐⭐⭐",
                recommended=True,
            ),
            ModelInfo(
                id="flux-general-en",
                name="Flux (英文)",
                pricing="$0.0077/分钟",
                accuracy="⭐⭐⭐⭐⭐",
            ),
            ModelInfo(
                id="nova-2-general",
                name="Nova-2 General",
                pricing="$0.0043/分钟",
                accuracy="⭐⭐⭐⭐",
            ),
        ],
    ),
    # Custom provider for user-defined OpenAI-compatible STT endpoints
    ProviderInfo(
        id="custom",
        name="自定义 (OpenAI Compatible)",
        base_url="",  # User must provide
        help_text="支持任何 OpenAI Whisper 兼容接口",
        models=[],  # User must input manually
    ),
]


# ==================== API Endpoint ====================


@router.get("/providers", response_model=ProvidersMetadataResponse)
async def get_providers_metadata() -> ProvidersMetadataResponse:
    """
    获取所有 Provider 的元数据配置

    返回 LLM 和 STT 的 Provider 列表，包括：
    - Provider ID 和名称
    - 默认 Base URL
    - 支持的模型列表（含价格、准确率、是否推荐）
    - 帮助文本（如何获取 API Key）
    """
    return ProvidersMetadataResponse(llm=LLM_PROVIDERS, stt=STT_PROVIDERS)
