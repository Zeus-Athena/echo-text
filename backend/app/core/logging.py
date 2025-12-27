"""
Logging Configuration
日志配置 - 支持开发环境彩色输出和生产环境 JSON 结构化

使用方法:
    from app.core.logging import setup_logging
    setup_logging()
"""

from __future__ import annotations

import json
import sys
from typing import Any

from loguru import logger

from app.core.config import settings


def json_serializer(record: dict) -> str:
    """将日志记录序列化为 JSON 格式"""
    log_entry = {
        "timestamp": record["time"].strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "level": record["level"].name,
        "message": record["message"],
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
    }

    # 添加 extra 字段
    if record["extra"]:
        # 过滤掉一些内部字段
        extra = {
            k: v
            for k, v in record["extra"].items()
            if not k.startswith("_") and k not in ("color",)
        }
        if extra:
            log_entry["extra"] = extra

    # 添加异常信息
    if record["exception"]:
        exc = record["exception"]
        log_entry["exception"] = {
            "type": exc.type.__name__ if exc.type else None,
            "value": str(exc.value) if exc.value else None,
            "traceback": "".join(exc.traceback.format()) if exc.traceback else None,
        }

    return json.dumps(log_entry, ensure_ascii=False, default=str)


def json_sink(message):
    """JSON 日志输出 sink"""
    record = message.record
    sys.stderr.write(json_serializer(record) + "\n")
    sys.stderr.flush()


# 彩色格式 (开发环境)
COLORED_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# 简单格式 (无颜色，用于日志文件)
PLAIN_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"


def setup_logging() -> None:
    """
    配置日志系统

    - development: 彩色格式输出到 stderr
    - production: JSON 格式输出到 stderr (便于日志收集工具解析)
    """
    # 移除默认 handler
    logger.remove()

    log_level = settings.LOG_LEVEL
    environment = settings.ENVIRONMENT

    if environment == "production":
        # 生产环境: JSON 格式
        logger.add(
            json_sink,
            level=log_level,
            backtrace=True,
            diagnose=False,  # 生产环境不显示变量值
        )
        logger.info("Logging configured", format="json", level=log_level)
    else:
        # 开发/测试环境: 彩色格式
        logger.add(
            sys.stderr,
            level=log_level,
            format=COLORED_FORMAT,
            backtrace=True,
            diagnose=True,
        )


def get_logger(name: str):
    """获取带有模块名的 logger"""
    return logger.bind(module=name)


# Request-scoped logging helpers
def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: str | None = None,
):
    """记录 HTTP 请求日志"""
    logger.info(
        f"{method} {path} - {status_code}",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=round(duration_ms, 2),
        user_id=user_id,
    )


def log_ws_event(
    event: str,
    client_id: str,
    details: dict[str, Any] | None = None,
):
    """记录 WebSocket 事件日志"""
    extra = {"event": event, "client_id": client_id}
    if details:
        extra.update(details)
    logger.debug(f"WS: {event}", **extra)


def log_external_call(
    service: str,
    provider: str,
    duration_ms: float,
    success: bool,
    error: str | None = None,
):
    """记录外部服务调用日志"""
    level = "info" if success else "warning"
    getattr(logger, level)(
        f"External call: {service}/{provider}",
        service=service,
        provider=provider,
        duration_ms=round(duration_ms, 2),
        success=success,
        error=error,
    )
