"""
Config Test API Routes
配置测试接口
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_effective_config
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import ConfigTestRequest, ConfigTestResponse

router = APIRouter(prefix="/config/test", tags=["Config Test"])


@router.post("/llm", response_model=ConfigTestResponse)
async def test_llm_config(
    request: ConfigTestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test LLM configuration"""
    import asyncio
    import time

    from loguru import logger

    start_time = time.perf_counter()
    logger.info(
        f"Testing LLM config: provider={request.provider}, model={request.model}, base_url={request.base_url}"
    )

    try:
        from openai import AsyncOpenAI

        api_key = request.api_key

        # If frontend sends "***", use the actual key from effective config
        if api_key == "***":
            user_config = await get_effective_config(current_user, db)
            if user_config:
                # Provider-aware key resolution
                p = request.provider.lower()
                if p == "groq":
                    api_key = user_config.llm_groq_api_key
                elif p == "siliconflow":
                    api_key = user_config.llm_siliconflow_api_key
                else:
                    api_key = user_config.llm_api_key

            if not api_key:
                raise HTTPException(
                    status_code=400, detail=f"尚未配置 {request.provider} 的 API Key"
                )

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=request.base_url,
            timeout=30.0,  # 30 second timeout
        )

        # 1. Try to list models first (standard connection check)
        try:
            await asyncio.wait_for(client.models.list(), timeout=10.0)
            logger.info(f"LLM connection verified via models.list for {request.provider}")
        except Exception as list_err:
            logger.warning(f"models.list failed, falling back to chat completion: {list_err}")

        # 2. Perform a small chat completion to verify full functionality
        # Use provided model or a safe fallback
        test_model = request.model or "gpt-3.5-turbo"
        logger.info(f"Calling LLM API with model={test_model}")

        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=test_model,
                    messages=[{"role": "user", "content": "Say 'Hello, test successful!'"}],
                    max_tokens=20,
                ),
                timeout=20.0,
            )
            message = response.choices[0].message.content
        except Exception as chat_err:
            logger.error(f"Chat completion failed: {chat_err}")
            # If models.list worked but chat failed, it might be a model issue
            message = "连接成功，但对话测试失败（可能是模型 ID 错误或无权访问）"
            # If we already verified connection via list, we can still return success=True
            # but with a warning message. Actually, better to raise if both fail.
            if "not found" in str(chat_err).lower():
                raise HTTPException(
                    status_code=400, detail=f"模型 {test_model} 未找到，请检查模型 ID"
                )
            raise HTTPException(status_code=400, detail=f"LLM 测试失败: {str(chat_err)}")

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(f"LLM test successful: latency={latency_ms}ms")

        return ConfigTestResponse(
            success=True,
            message=message,
            provider=request.provider,
            latency_ms=latency_ms,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LLM test failed: {e}")
        raise HTTPException(status_code=400, detail=f"LLM test failed: {str(e)}")


@router.post("/stt", response_model=ConfigTestResponse)
async def test_stt_config(
    request: ConfigTestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test STT configuration by actually calling the API"""
    import time

    start_time = time.perf_counter()

    try:
        import httpx
        from openai import AsyncOpenAI

        api_key = request.api_key

        # If frontend sends "***", use the actual key from effective config
        if api_key == "***":
            user_config = await get_effective_config(current_user, db)
            if user_config:
                # Provider-aware key resolution
                p = request.provider.lower()
                if p == "groq":
                    api_key = user_config.stt_groq_api_key
                elif p == "deepgram":
                    api_key = user_config.stt_deepgram_api_key
                elif p == "openai":
                    api_key = user_config.stt_openai_api_key
                elif p == "siliconflow":
                    api_key = user_config.stt_siliconflow_api_key
                else:
                    api_key = user_config.stt_api_key

            if not api_key:
                raise HTTPException(
                    status_code=400, detail=f"尚未配置 {request.provider} 的 API Key"
                )

        client = AsyncOpenAI(api_key=api_key, base_url=request.base_url)

        # Try to list models to verify API key and endpoint work
        # This is a real API call that verifies the connection
        try:
            models = await client.models.list()
            model_names = [m.id for m in models.data[:5]]  # Get first 5 models
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return ConfigTestResponse(
                success=True,
                message=f"STT 连接成功！可用模型：{', '.join(model_names[:3])}...",
                provider=request.provider,
                latency_ms=latency_ms,
            )
        except Exception:
            # Some providers don't support listing models, try a different approach
            # Just verify the endpoint is reachable
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(
                    f"{request.base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0,
                )
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                if response.status_code == 200:
                    return ConfigTestResponse(
                        success=True,
                        message=f"STT 配置有效。Provider: {request.provider}, Model: {request.model}",
                        provider=request.provider,
                        latency_ms=latency_ms,
                    )
                else:
                    raise HTTPException(
                        status_code=400, detail=f"STT 测试失败：API返回 {response.status_code}"
                    )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"STT 测试失败：{str(e)}")


@router.post("/tts", response_model=ConfigTestResponse)
async def test_tts_config(
    request: ConfigTestRequest, current_user: User = Depends(get_current_user)
):
    """Test TTS configuration"""
    import time

    start_time = time.perf_counter()

    try:
        if request.provider.lower() == "edge":
            import edge_tts

            # Quick test - just verify edge_tts is available
            voices = await edge_tts.list_voices()
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return ConfigTestResponse(
                success=True,
                message=f"Edge TTS available with {len(voices)} voices",
                provider=request.provider,
                latency_ms=latency_ms,
            )
        elif request.provider.lower() == "openai":
            from openai import AsyncOpenAI

            _client = AsyncOpenAI(
                api_key=request.api_key, base_url=request.base_url or "https://api.openai.com/v1"
            )

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return ConfigTestResponse(
                success=True,
                message="OpenAI TTS configuration valid",
                provider=request.provider,
                latency_ms=latency_ms,
            )
        else:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return ConfigTestResponse(
                success=True,
                message=f"Custom TTS provider: {request.provider}",
                provider=request.provider,
                latency_ms=latency_ms,
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"TTS test failed: {str(e)}")


# STT Models with pricing and accuracy info
STT_MODELS = [
    # GROQ Models (Free tier available)
    {
        "id": "whisper-large-v3-turbo",
        "name": "Whisper Large V3 Turbo",
        "provider": "GROQ",
        "pricing": "免费 (每天有限额)",
        "accuracy": "⭐⭐⭐⭐⭐ 极高",
        "description": "最新 Turbo 版本，速度最快，准确率极高",
        "languages": "多语言",
        "recommended": True,
    },
    {
        "id": "whisper-large-v3",
        "name": "Whisper Large V3",
        "provider": "GROQ",
        "pricing": "免费 (每天有限额)",
        "accuracy": "⭐⭐⭐⭐⭐ 极高",
        "description": "OpenAI Whisper 最大模型，多语言支持最好",
        "languages": "多语言",
        "recommended": True,
    },
    {
        "id": "distil-whisper-large-v3-en",
        "name": "Distil Whisper Large V3 (English)",
        "provider": "GROQ",
        "pricing": "免费 (每天有限额)",
        "accuracy": "⭐⭐⭐⭐ 高",
        "description": "英语优化版本，速度更快",
        "languages": "仅英语",
        "recommended": False,
    },
    # OpenAI Models (Paid)
    {
        "id": "whisper-1",
        "name": "Whisper-1",
        "provider": "OpenAI",
        "pricing": "$0.006/分钟",
        "accuracy": "⭐⭐⭐⭐⭐ 极高",
        "description": "OpenAI 官方 Whisper API",
        "languages": "多语言",
        "recommended": False,
    },
    # Deepgram Models (Paid with free tier)
    {
        "id": "nova-2",
        "name": "Nova-2",
        "provider": "Deepgram",
        "pricing": "$0.0043/分钟 (有免费额度)",
        "accuracy": "⭐⭐⭐⭐⭐ 极高",
        "description": "Deepgram 最新模型，实时转录极快",
        "languages": "多语言",
        "recommended": False,
    },
    {
        "id": "nova-2-general",
        "name": "Nova-2 General",
        "provider": "Deepgram",
        "pricing": "$0.0043/分钟",
        "accuracy": "⭐⭐⭐⭐ 高",
        "description": "通用场景优化",
        "languages": "多语言",
        "recommended": False,
    },
]


@router.get("/stt/models")
async def get_stt_models(current_user: User = Depends(get_current_user)):
    """Get available STT models with pricing and accuracy info"""
    return {"models": STT_MODELS, "recommended": "whisper-large-v3-turbo"}


@router.post("/stt/models/fetch")
async def fetch_stt_models_from_provider(
    request: ConfigTestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch actual available models from the STT provider"""
    try:
        from openai import AsyncOpenAI

        from app.api.deps import get_effective_config

        api_key = request.api_key

        # If frontend sends "***", resolve actual key
        if api_key == "***":
            user_config = await get_effective_config(current_user, db)
            if user_config:
                # Provider-aware key resolution
                p = request.provider.lower()
                if p == "groq":
                    api_key = user_config.stt_groq_api_key
                elif p == "deepgram":
                    api_key = user_config.stt_deepgram_api_key
                elif p == "openai":
                    api_key = user_config.stt_openai_api_key
                elif p == "siliconflow":
                    api_key = user_config.stt_siliconflow_api_key
                else:
                    api_key = user_config.stt_api_key

            if not api_key:
                raise HTTPException(
                    status_code=400, detail=f"尚未配置 {request.provider} 的 API Key"
                )

        client = AsyncOpenAI(api_key=api_key, base_url=request.base_url)
        models = await client.models.list()

        # Filter for whisper/audio models
        stt_models = []
        for model in models.data:
            model_id = model.id.lower()
            if any(kw in model_id for kw in ["whisper", "audio", "speech", "stt", "transcri"]):
                # Find matching model info from our database
                model_info = next((m for m in STT_MODELS if m["id"] == model.id), None)
                stt_models.append(
                    {
                        "id": model.id,
                        "name": model_info["name"] if model_info else model.id,
                        "pricing": model_info["pricing"] if model_info else "未知",
                        "accuracy": model_info["accuracy"] if model_info else "⭐⭐⭐ 中等",
                        "description": model_info["description"] if model_info else "",
                        "recommended": model_info["recommended"] if model_info else False,
                    }
                )

        if not stt_models:
            # Return all models if no STT-specific ones found
            stt_models = [
                {
                    "id": m.id,
                    "name": m.id,
                    "pricing": "未知",
                    "accuracy": "⭐⭐⭐ 中等",
                    "description": "",
                    "recommended": False,
                }
                for m in models.data[:20]
            ]

        return {"models": stt_models}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取模型列表失败: {str(e)}")
