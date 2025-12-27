"""
Search API Routes
全文搜索接口
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.fts_service import FullTextSearchService

router = APIRouter(prefix="/search", tags=["Search"])


class SearchResultItem(BaseModel):
    """搜索结果项"""

    recording_id: UUID
    title: str
    matched_field: str  # 'title' | 'transcript' | 'summary'
    matched_content: str  # 匹配的内容片段（带高亮标记）
    relevance_score: float

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """搜索响应"""

    query: str
    total: int
    results: list[SearchResultItem]


@router.get("/", response_model=SearchResponse)
async def full_text_search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    search_in: str | None = Query(
        "all", description="搜索范围：all | title | transcript | summary，多个用逗号分隔"
    ),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    全文搜索录音内容

    支持搜索：
    - 录音标题
    - 转录内容 (transcript)
    - AI 总结 (summary)

    返回匹配的录音列表，包含高亮的匹配片段。
    """
    # 解析搜索范围
    if search_in == "all":
        search_fields = ["title", "transcript", "summary"]
    else:
        search_fields = [s.strip() for s in search_in.split(",")]
        # 验证字段名
        valid_fields = {"title", "transcript", "summary"}
        search_fields = [f for f in search_fields if f in valid_fields]
        if not search_fields:
            search_fields = ["title", "transcript", "summary"]

    # 执行搜索
    fts_service = FullTextSearchService(db)
    results = await fts_service.search(
        query=q, user_id=current_user.id, search_in=search_fields, limit=limit, offset=offset
    )

    # 转换为响应格式
    return SearchResponse(
        query=q,
        total=len(results),
        results=[
            SearchResultItem(
                recording_id=r.recording_id,
                title=r.title,
                matched_field=r.matched_field,
                matched_content=r.matched_content,
                relevance_score=r.relevance_score,
            )
            for r in results
        ],
    )
