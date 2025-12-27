"""
API v1 Router
汇总所有 API 路由
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.config import router as config_router
from app.api.v1.diarization import router as diarization_router
from app.api.v1.export import router as export_router
from app.api.v1.prompts import router as prompts_router
from app.api.v1.recordings import router as recordings_router
from app.api.v1.search import router as search_router
from app.api.v1.share import router as share_router
from app.api.v1.translate import router as translate_router
from app.api.v1.users import router as users_router
from app.api.v1.ws_v2 import router as ws_router  # WebSocket transcription

api_router = APIRouter()

# Include all routers
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(recordings_router)
api_router.include_router(translate_router)
api_router.include_router(config_router)
api_router.include_router(ws_router)
api_router.include_router(search_router)
api_router.include_router(export_router)
api_router.include_router(share_router)
api_router.include_router(diarization_router)
api_router.include_router(prompts_router, prefix="/prompts", tags=["prompts"])
