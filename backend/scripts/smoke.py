"""DataQnA 端到端冒烟：L1-L5 五个等级各跑一个示例问题，校验事件流完整闭合。

前置条件：
  1. docker compose 起 postgres/redis（deploy/docker-compose.yml）
  2. 已灌种子数据：uv run python -m app.seed
用法：
  uv run python scripts/smoke.py
退出码：全部 PASS 为 0，任一 FAIL 为 1。
"""
from __future__ import annotations

import asyncio

from app.core.container import get_container
from app.dsl.compiler import SecurityContext
from app.observability.span import Tracer

CASES: list[tuple[str, str]] = [
    ("L1", "上月GMV是多少"),
    ("L2", "近30天各品类的退款率"),
    ("L3", "上月退款率环比"),
    ("L4", "为什么退款率环比上升了，是哪个大区导致的"),
    ("L5", "本月GMV、订单数和退款率"),
]


async def run_case(question: str) -> tuple[bool, str]:
    """跑一个问数，返回 (是否闭合, 摘要)。闭合 = 有 answer + done 且无 error。"""
    c = get_container()
    ctx = SecurityContext(tenant_id="t1")
    types: list[str] = []
    answer_value: object | None = None
    async for ev in c.orchestrator.run(question, ctx, roles_hash="smoke", tracer=Tracer()):
        t = ev.get("type", "")
        types.append(t)
        if t == "answer":
            answer_value = ev.get("value")
        if t == "error":
            detail = ev.get("error", {}).get("detail", "")
            return False, f"error: {detail}"
    ok = "answer" in types and "done" in types
    return ok, f"answer={answer_value!r} subgoals={types.count('subgoal_completed')}"


async def main() -> int:
    print("== DataQnA 端到端冒烟（L1-L5）==", flush=True)
    failed = 0
    for level, q in CASES:
        ok, summary = await run_case(q)
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"[{level}] {mark} :: {q!r} -> {summary}", flush=True)
    print(f"== 冒烟完成：{len(CASES) - failed}/{len(CASES)} PASS ==", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
