"""
Provider Configuration Schemas
Provider 配置元数据接口
"""

from pydantic import BaseModel


class ModelInfo(BaseModel):
    """单个模型信息"""

    id: str
    name: str
    pricing: str
    accuracy: str | None = None  # STT 专用
    recommended: bool = False


class ProviderInfo(BaseModel):
    """Provider 元数据"""

    id: str
    name: str
    base_url: str
    models: list[ModelInfo]
    help_text: str | None = None


class ProvidersMetadataResponse(BaseModel):
    """Provider 元数据完整响应"""

    llm: list[ProviderInfo]
    stt: list[ProviderInfo]
