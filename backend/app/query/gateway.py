"""查询网关：只读执行、成本计量（EXPLAIN 估算）、结果缓存。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import asyncpg

from app.core.config import settings
from app.core.logging import get_logger
from app.dsl.compiler import CompiledQuery, SecurityContext

logger = get_logger()


@dataclass
class QueryResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    scanned_bytes: int = 0
    latency_ms: float = 0.0
    cache_hit: bool = False


def _cache_key(
    compiled: CompiledQuery, ctx: SecurityContext, semantic_version: int, roles_hash: str,
) -> str:
    return f"{compiled.dsl_fingerprint}|{semantic_version}|{ctx.tenant_id}|{roles_hash}"


class QueryGateway:
    """分析查询执行器。持有只读连接池，RLS 通过 SET app.tenant_id 生效。"""

    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None
        self._cache: dict[str, tuple[float, QueryResult]] = {}
        self._ttl = 15 * 60  # 15 分钟

    def clear_cache(self) -> None:
        """清空结果缓存（评测 A/B 需「连接池已预热但缓存冷」以消除缓存噪声）。"""
        self._cache.clear()

    async def _ensure_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            dsn = settings.analytics_url.replace("+asyncpg", "")
            self._pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        return self._pool

    async def execute(
        self,
        compiled: CompiledQuery,
        ctx: SecurityContext,
        semantic_version: int,
        roles_hash: str,
    ) -> QueryResult:
        key = _cache_key(compiled, ctx, semantic_version, roles_hash)
        now = time.time()
        cached = self._cache.get(key)
        if cached and cached[0] > now:
            cached[1].cache_hit = True
            return cached[1]

        pool = await self._ensure_pool()
        start = time.monotonic()
        async with pool.acquire() as conn, conn.transaction():
            # RLS：设置租户上下文（事务级，事务结束自动清除，不污染连接池）
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", ctx.tenant_id)

            # 成本估算：EXPLAIN 提取预估扫描行数
            scanned = await self._estimate_scanned(conn, compiled)

            rows = await conn.fetch(compiled.sql, *compiled.params)
            columns = [k for k in rows[0]] if rows else []
            result_rows = [dict(r) for r in rows]

        latency = (time.monotonic() - start) * 1000
        result = QueryResult(
            rows=result_rows, columns=columns, scanned_bytes=scanned, latency_ms=latency,
        )
        self._cache[key] = (now + self._ttl, result)
        logger.info(
            "query_executed", sql_fp=compiled.sql_fingerprint, rows=len(result_rows),
            scanned_bytes=scanned, latency_ms=round(latency, 1),
        )
        return result

    async def _estimate_scanned(self, conn: asyncpg.Connection, compiled: CompiledQuery) -> int:
        try:
            plan = await conn.fetchval(
                "EXPLAIN (FORMAT JSON) " + compiled.sql, *compiled.params
            )
            import json

            root = json.loads(plan)[0]["Plan"]
            total_rows = int(root.get("Plan Rows", 0))
            # 估算：平均行长 256 字节
            return total_rows * 256
        except Exception:
            return 0
