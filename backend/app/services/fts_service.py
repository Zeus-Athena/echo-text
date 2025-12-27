"""
Full-Text Search Service
全文搜索服务 - 支持 SQLite FTS5 和 PostgreSQL Full Text Search
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


@dataclass
class SearchResult:
    """搜索结果"""

    recording_id: UUID
    title: str
    matched_field: str  # 'title' | 'transcript' | 'summary'
    matched_content: str  # 匹配的内容片段
    relevance_score: float


class FullTextSearchService:
    """
    统一的全文搜索服务
    自动检测数据库类型并使用对应的 FTS 实现
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._is_postgresql = self._detect_postgresql()

    def _detect_postgresql(self) -> bool:
        """检测是否使用 PostgreSQL"""
        return "postgresql" in settings.DATABASE_URL.lower()

    async def search(
        self,
        query: str,
        user_id: UUID,
        search_in: list[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[SearchResult]:
        """
        执行全文搜索

        Args:
            query: 搜索关键词
            user_id: 用户 ID
            search_in: 搜索范围 ['title', 'transcript', 'summary']，默认全部
            limit: 返回结果数量
            offset: 分页偏移

        Returns:
            搜索结果列表
        """
        if not query or not query.strip():
            return []

        search_in = search_in or ["title", "transcript", "summary"]

        if self._is_postgresql:
            return await self._pg_search(query, user_id, search_in, limit, offset)
        else:
            return await self._sqlite_search(query, user_id, search_in, limit, offset)

    async def _pg_search(
        self, query: str, user_id: UUID, search_in: list[str], limit: int, offset: int
    ) -> list[SearchResult]:
        """PostgreSQL 全文搜索实现"""
        results = []

        # 构建搜索查询 - 使用 plainto_tsquery 处理中文
        ts_query = "plainto_tsquery('simple', :query)"

        # 搜索标题
        if "title" in search_in:
            sql = text(f"""
                SELECT 
                    r.id as recording_id,
                    r.title,
                    'title' as matched_field,
                    r.title as matched_content,
                    ts_rank(to_tsvector('simple', r.title), {ts_query}) as relevance
                FROM recordings r
                WHERE r.user_id = :user_id
                AND to_tsvector('simple', r.title) @@ {ts_query}
                ORDER BY relevance DESC
                LIMIT :limit OFFSET :offset
            """)

            result = await self.db.execute(
                sql, {"query": query, "user_id": str(user_id), "limit": limit, "offset": offset}
            )
            for row in result.fetchall():
                results.append(
                    SearchResult(
                        recording_id=UUID(str(row.recording_id)),
                        title=row.title,
                        matched_field=row.matched_field,
                        matched_content=row.matched_content,
                        relevance_score=float(row.relevance),
                    )
                )

        # 搜索转录内容
        if "transcript" in search_in:
            sql = text(f"""
                SELECT 
                    r.id as recording_id,
                    r.title,
                    'transcript' as matched_field,
                    ts_headline('simple', t.full_text, {ts_query}, 
                        'MaxWords=30, MinWords=15, StartSel=<mark>, StopSel=</mark>'
                    ) as matched_content,
                    ts_rank(to_tsvector('simple', t.full_text), {ts_query}) as relevance
                FROM recordings r
                JOIN transcripts t ON t.recording_id = r.id
                WHERE r.user_id = :user_id
                AND to_tsvector('simple', t.full_text) @@ {ts_query}
                ORDER BY relevance DESC
                LIMIT :limit OFFSET :offset
            """)

            result = await self.db.execute(
                sql, {"query": query, "user_id": str(user_id), "limit": limit, "offset": offset}
            )
            for row in result.fetchall():
                results.append(
                    SearchResult(
                        recording_id=UUID(str(row.recording_id)),
                        title=row.title,
                        matched_field=row.matched_field,
                        matched_content=row.matched_content or "",
                        relevance_score=float(row.relevance),
                    )
                )

        # 搜索 AI 总结
        if "summary" in search_in:
            sql = text(f"""
                SELECT 
                    r.id as recording_id,
                    r.title,
                    'summary' as matched_field,
                    ts_headline('simple', s.summary, {ts_query},
                        'MaxWords=30, MinWords=15, StartSel=<mark>, StopSel=</mark>'
                    ) as matched_content,
                    ts_rank(to_tsvector('simple', s.summary), {ts_query}) as relevance
                FROM recordings r
                JOIN ai_summaries s ON s.recording_id = r.id
                WHERE r.user_id = :user_id
                AND to_tsvector('simple', s.summary) @@ {ts_query}
                ORDER BY relevance DESC
                LIMIT :limit OFFSET :offset
            """)

            result = await self.db.execute(
                sql, {"query": query, "user_id": str(user_id), "limit": limit, "offset": offset}
            )
            for row in result.fetchall():
                results.append(
                    SearchResult(
                        recording_id=UUID(str(row.recording_id)),
                        title=row.title,
                        matched_field=row.matched_field,
                        matched_content=row.matched_content or "",
                        relevance_score=float(row.relevance),
                    )
                )

        # 按相关性排序并去重
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:limit]

    async def _sqlite_search(
        self, query: str, user_id: UUID, search_in: list[str], limit: int, offset: int
    ) -> list[SearchResult]:
        """SQLite 全文搜索实现 (使用 LIKE 模糊匹配，后续可升级为 FTS5)"""
        results = []
        search_pattern = f"%{query}%"

        # 搜索标题
        if "title" in search_in:
            sql = text("""
                SELECT 
                    r.id as recording_id,
                    r.title,
                    'title' as matched_field,
                    r.title as matched_content
                FROM recordings r
                WHERE r.user_id = :user_id
                AND r.title LIKE :pattern
                LIMIT :limit OFFSET :offset
            """)

            result = await self.db.execute(
                sql,
                {
                    "user_id": str(user_id),
                    "pattern": search_pattern,
                    "limit": limit,
                    "offset": offset,
                },
            )
            for row in result.fetchall():
                results.append(
                    SearchResult(
                        recording_id=UUID(str(row.recording_id)),
                        title=row.title,
                        matched_field=row.matched_field,
                        matched_content=self._highlight_match(row.matched_content, query),
                        relevance_score=1.0,
                    )
                )

        # 搜索转录内容
        if "transcript" in search_in:
            sql = text("""
                SELECT 
                    r.id as recording_id,
                    r.title,
                    'transcript' as matched_field,
                    t.full_text as matched_content
                FROM recordings r
                JOIN transcripts t ON t.recording_id = r.id
                WHERE r.user_id = :user_id
                AND t.full_text LIKE :pattern
                LIMIT :limit OFFSET :offset
            """)

            result = await self.db.execute(
                sql,
                {
                    "user_id": str(user_id),
                    "pattern": search_pattern,
                    "limit": limit,
                    "offset": offset,
                },
            )
            for row in result.fetchall():
                # 提取匹配片段
                snippet = self._extract_snippet(row.matched_content or "", query, max_length=100)
                results.append(
                    SearchResult(
                        recording_id=UUID(str(row.recording_id)),
                        title=row.title,
                        matched_field=row.matched_field,
                        matched_content=self._highlight_match(snippet, query),
                        relevance_score=0.8,
                    )
                )

        # 搜索 AI 总结
        if "summary" in search_in:
            sql = text("""
                SELECT 
                    r.id as recording_id,
                    r.title,
                    'summary' as matched_field,
                    s.summary as matched_content
                FROM recordings r
                JOIN ai_summaries s ON s.recording_id = r.id
                WHERE r.user_id = :user_id
                AND s.summary LIKE :pattern
                LIMIT :limit OFFSET :offset
            """)

            result = await self.db.execute(
                sql,
                {
                    "user_id": str(user_id),
                    "pattern": search_pattern,
                    "limit": limit,
                    "offset": offset,
                },
            )
            for row in result.fetchall():
                snippet = self._extract_snippet(row.matched_content or "", query, max_length=100)
                results.append(
                    SearchResult(
                        recording_id=UUID(str(row.recording_id)),
                        title=row.title,
                        matched_field=row.matched_field,
                        matched_content=self._highlight_match(snippet, query),
                        relevance_score=0.6,
                    )
                )

        # 按相关性排序
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:limit]

    def _extract_snippet(self, text: str, query: str, max_length: int = 100) -> str:
        """从文本中提取包含关键词的片段"""
        if not text:
            return ""

        query_lower = query.lower()
        text_lower = text.lower()

        pos = text_lower.find(query_lower)
        if pos == -1:
            return text[:max_length] + "..." if len(text) > max_length else text

        # 提取关键词周围的片段
        start = max(0, pos - max_length // 2)
        end = min(len(text), pos + len(query) + max_length // 2)

        snippet = text[start:end]

        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet

    def _highlight_match(self, text: str, query: str) -> str:
        """高亮匹配的关键词"""
        if not text or not query:
            return text

        import re

        pattern = re.compile(re.escape(query), re.IGNORECASE)
        return pattern.sub(f"<mark>{query}</mark>", text)
