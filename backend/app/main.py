"""
EchoText Backend - FastAPI Application
实时转录翻译系统后端
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.__version__ import __version__
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging

# Import all models so they register with Base
from app.models import *  # noqa

# Configure logging (JSON in production, colored in development)
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("🚀 Starting EchoText Backend...")
    logger.info(f"📝 Environment: {settings.ENVIRONMENT}")
    # Initialize database tables
    await init_db()
    logger.info("✅ Database tables initialized")
    yield
    logger.info("👋 Shutting down EchoText Backend...")


app = FastAPI(
    title="EchoText API",
    description="实时转录翻译系统 API",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register custom exception handlers
from app.core.exception_handlers import register_exception_handlers

register_exception_handlers(app)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Enhanced health check with dependency status"""
    import redis.asyncio as redis
    from sqlalchemy import text

    from app.core.database import async_session

    result = {
        "status": "healthy",
        "version": __version__,
        "checks": {},
    }

    # Check PostgreSQL / SQLite
    db_type = "postgresql" if "postgresql" in settings.DATABASE_URL else "sqlite"
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        result["checks"][db_type] = "ok"
    except Exception as e:
        result["checks"][db_type] = f"error: {type(e).__name__}"
        result["status"] = "degraded"

    # Check Redis (optional, don't mark as degraded if unavailable)
    try:
        redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
        r = redis.from_url(redis_url)
        await r.ping()
        await r.aclose()
        result["checks"]["redis"] = "ok"
    except Exception:
        result["checks"]["redis"] = "unavailable"

    return result


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to EchoText API", "docs": "/docs", "version": __version__}
