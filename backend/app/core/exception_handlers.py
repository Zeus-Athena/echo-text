"""
Exception Handlers
全局异常处理器，将自定义异常转换为 HTTP 响应
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.exceptions import (
    AudioProcessingError,
    AuthenticationError,
    ConfigurationError,
    DiarizationServiceError,
    EchoTextError,
    ExternalServiceError,
    InvalidTokenError,
    LLMServiceError,
    PermissionDeniedError,
    RateLimitError,
    ResourceExistsError,
    ResourceNotFoundError,
    STTServiceError,
    TokenExpiredError,
    TTSServiceError,
    ValidationError,
)


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器"""

    @app.exception_handler(InvalidTokenError)
    async def invalid_token_handler(request: Request, exc: InvalidTokenError):
        return JSONResponse(
            status_code=401,
            content={"detail": exc.message},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(TokenExpiredError)
    async def token_expired_handler(request: Request, exc: TokenExpiredError):
        return JSONResponse(
            status_code=401,
            content={"detail": exc.message},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(
            status_code=401,
            content={"detail": exc.message},
        )

    @app.exception_handler(PermissionDeniedError)
    async def permission_denied_handler(request: Request, exc: PermissionDeniedError):
        return JSONResponse(
            status_code=403,
            content={"detail": exc.message},
        )

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"detail": exc.message},
        )

    @app.exception_handler(ResourceExistsError)
    async def resource_exists_handler(request: Request, exc: ResourceExistsError):
        return JSONResponse(
            status_code=409,
            content={"detail": exc.message},
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.message, "field": exc.field},
        )

    @app.exception_handler(RateLimitError)
    async def rate_limit_handler(request: Request, exc: RateLimitError):
        headers = {}
        if exc.retry_after:
            headers["Retry-After"] = str(exc.retry_after)
        return JSONResponse(
            status_code=429,
            content={"detail": exc.message, "service": exc.service},
            headers=headers,
        )

    @app.exception_handler(STTServiceError)
    async def stt_error_handler(request: Request, exc: STTServiceError):
        logger.error(f"STT Service Error: {exc.message}", provider=exc.provider)
        return JSONResponse(
            status_code=502,
            content={
                "detail": exc.message,
                "service": "stt",
                "provider": exc.provider,
            },
        )

    @app.exception_handler(LLMServiceError)
    async def llm_error_handler(request: Request, exc: LLMServiceError):
        logger.error(f"LLM Service Error: {exc.message}", provider=exc.provider)
        return JSONResponse(
            status_code=502,
            content={
                "detail": exc.message,
                "service": "llm",
                "provider": exc.provider,
            },
        )

    @app.exception_handler(TTSServiceError)
    async def tts_error_handler(request: Request, exc: TTSServiceError):
        logger.error(f"TTS Service Error: {exc.message}", provider=exc.provider)
        return JSONResponse(
            status_code=502,
            content={
                "detail": exc.message,
                "service": "tts",
                "provider": exc.provider,
            },
        )

    @app.exception_handler(DiarizationServiceError)
    async def diarization_error_handler(request: Request, exc: DiarizationServiceError):
        logger.error(f"Diarization Service Error: {exc.message}", provider=exc.provider)
        return JSONResponse(
            status_code=502,
            content={
                "detail": exc.message,
                "service": "diarization",
                "provider": exc.provider,
            },
        )

    @app.exception_handler(ExternalServiceError)
    async def external_service_handler(request: Request, exc: ExternalServiceError):
        logger.error(f"External Service Error: {exc.message}", service=exc.service)
        return JSONResponse(
            status_code=502,
            content={"detail": exc.message, "service": exc.service},
        )

    @app.exception_handler(AudioProcessingError)
    async def audio_processing_handler(request: Request, exc: AudioProcessingError):
        logger.warning(f"Audio Processing Error: {exc.message}")
        return JSONResponse(
            status_code=400,
            content={"detail": exc.message},
        )

    @app.exception_handler(ConfigurationError)
    async def config_error_handler(request: Request, exc: ConfigurationError):
        logger.error(f"Configuration Error: {exc.message}")
        return JSONResponse(
            status_code=500,
            content={"detail": exc.message},
        )

    @app.exception_handler(EchoTextError)
    async def echotext_error_handler(request: Request, exc: EchoTextError):
        """兜底处理所有 EchoTextError"""
        logger.error(f"EchoText Error: {exc.message}")
        return JSONResponse(
            status_code=500,
            content={"detail": exc.message},
        )
