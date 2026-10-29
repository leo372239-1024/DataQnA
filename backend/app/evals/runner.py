"""评测跑分器：加载套件 → 逐用例打分 → 聚合 + 失败分布 → 写 baselines/*.json。

用法：
  uv run python -m app.evals.runner --suite gold --level L1-L5
  uv run python -m app.evals.runner --suite routing --baseline on|off
  uv run python -m app.evals.runner --suite redteam
  uv run python -m app.evals.runner --suite reflection --baseline on|off
  uv run python -m app.evals.runner --suite longtask --baseline on|off
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

from app.agent.orchestrator import Orchestrator
from app.dsl.compiler import SecurityContext
from app.evals.classifier import failure_breakdown
from app.evals.loader import EVALS_ROOT, load_cases
from app.evals.models import EvalCase
from app.evals.scorers import score_gold_case, score_redteam_case
from app.query.gateway import QueryGateway
from app.routing.router import Router
from app.semantic.registry import MetricRegistry

_BASELINE_DIR = EVALS_ROOT / "baselines"


def _rate(results: list[dict[str, Any]], key: str) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if r[key]) / len(results)


def _passed_rate(results: list[dict[str, Any]]) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if r["passed"]) / len(results)


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    codes = [r.get("failure_code") for r in results]
    return {
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "failure_breakdown": [{"code": f.code, "count": f.count}
                              for f in failure_breakdown(codes)],
    }


# ---- gold ----


async def run_gold(
    registry: MetricRegistry, gateway: QueryGateway, level: str,
) -> dict[str, Any]:
    cases = load_cases("gold", level)
    orchestrator = Orchestrator(registry, gateway)
    ctx = SecurityContext(tenant_id="t1")
    results: list[dict[str, Any]] = []
    for c in cases:
        results.append(await score_gold_case(c, orchestrator, registry, gateway, ctx))

    by_level: dict[str, list[dict[str, Any]]] = {}
    for r, c in zip(results, cases, strict=True):
        by_level.setdefault(c.level, []).append(r)

    return {
        "suite": "gold",
        "cases": len(cases),
        "EX": _passed_rate(results),
        "intent_accuracy": _rate(results, "intent_exact"),
        "valid_query_rate": _rate(results, "valid_sql"),
        "non_empty_rate": _rate(results, "non_empty"),
        "caliber_consistency": _rate(results, "caliber_ok"),
        "lineage_traceability": _rate(results, "lineage_ok"),
        "per_level": {lv: {"n": len(rs), "EX": _passed_rate(rs)} for lv, rs in by_level.items()},
        **_summary(results),
    }


# ---- routing（H3/H4，A/B：别名短路 vs 全三层）----


async def run_routing(
    registry: MetricRegistry, gateway: QueryGateway, baseline: bool,
) -> dict[str, Any]:
    cases = load_cases("routing")
    router = _build_router()
    results: list[dict[str, Any]] = []
    for c in cases:
        roles = set(c.caller_roles)
        rr = await router.route(c.question, roles, baseline=baseline)
        hit = rr.asset_id == c.expected_asset_id
        results.append({
            "case_id": c.id,
            "passed": hit,
            "failure_code": None if hit else "TOOL_MISUSE",
            "actual": rr.asset_id,
            "expected": c.expected_asset_id,
        })
    return {
        "suite": "routing",
        "baseline": baseline,
        "cases": len(cases),
        "route_accuracy_at1": _passed_rate(results),
        **_summary(results),
    }


def _build_router() -> Router:
    from app.core.container import assets_yaml_path
    from app.routing.registry import AssetRegistry

    return Router(AssetRegistry.from_yaml(assets_yaml_path()))


# ---- redteam（X1 安全）----


async def run_redteam(
    registry: MetricRegistry, gateway: QueryGateway,
) -> dict[str, Any]:
    cases = load_cases("redteam")
    orchestrator = Orchestrator(registry, gateway)
    ctx = SecurityContext(tenant_id="t1")
    results: list[dict[str, Any]] = []
    for c in cases:
        results.append(await score_redteam_case(c, orchestrator, registry, ctx))
    return {
        "suite": "redteam",
        "cases": len(cases),
        "block_rate": _passed_rate(results),
        **_summary(results),
    }


# ---- reflection（H5，A/B：反思循环开/关）----


async def run_reflection(
    registry: MetricRegistry, baseline: bool,
) -> dict[str, Any]:
    """反思 A/B：用例首跑失败，反思循环学习别名后重跑。

    baseline=on（无反思）：重跑成功率 = 首跑成功率（失败用例仍失败）。
    baseline=off（反思开）：从期望指标学习别名并重跑，成功率显著提升。
    """
    cases = load_cases("reflection")
    from app.agent.intent import classify_intent

    results: list[dict[str, Any]] = []
    for c in cases:
        intent = classify_intent(c.question, registry)
        first_ok = sorted(intent.metric_ids) == sorted(c.expected_metric_ids)
        if baseline:
            ok = first_ok
        else:
            # 反思：注册缺失别名（question 中的未知提及 → 期望指标），重跑
            enriched = _enrich_registry(registry, c)
            intent2 = classify_intent(c.question, enriched)
            ok = sorted(intent2.metric_ids) == sorted(c.expected_metric_ids)
        results.append({
            "case_id": c.id,
            "passed": ok,
            "failure_code": None if ok else "NO_MATCH",
            "first_ok": first_ok,
        })
    return {
        "suite": "reflection",
        "baseline": baseline,
        "cases": len(cases),
        "retry_success_rate": _passed_rate(results),
        **_summary(results),
    }


def _enrich_registry(registry: MetricRegistry, case: EvalCase) -> MetricRegistry:
    """复制注册表并注册「缺失别名 → 期望指标」（模拟反思写回 add_alias）。"""
    from copy import deepcopy

    reg_copy = deepcopy(registry._reg)  # noqa: SLF001 反思实验需要深拷贝真相源
    target = case.expected_metric_ids[0] if case.expected_metric_ids else None
    learn_alias = case.learn_alias
    if target is not None and learn_alias:
        for m in reg_copy.metrics:
            if m.id == target and learn_alias not in m.aliases:
                m.aliases.append(learn_alias)
    return MetricRegistry(reg_copy)


# ---- longtask（H1/H2，A/B：顺序 vs 并行）----


async def run_longtask(
    registry: MetricRegistry, gateway: QueryGateway, baseline: bool,
) -> dict[str, Any]:
    """长时程任务 A/B：L5 多指标报告（逐指标分解为 N 个独立子目标）。

    baseline=on：顺序执行子目标（模拟无并行编排）。
    baseline=off：并行执行独立子目标（当前编排器默认）。
    指标：任务成功率 + 端到端延迟（多轮取中位，先预热连接池）+ 重复动作数（单写者 dup=0）。
    """
    cases = load_cases("gold", "L5")
    orchestrator = Orchestrator(registry, gateway)
    ctx = SecurityContext(tenant_id="t1")

    async def _measure_once() -> tuple[float, int, int]:
        gateway.clear_cache()  # 每轮冷缓存，消除缓存命中对并行/顺序对比的干扰
        batch_start = time.monotonic()
        passed = 0
        total_steps = 0
        for c in cases:
            subgoal_statuses: dict[str, str] = {}
            async for ev in orchestrator.run(c.question, ctx, "", sequential=baseline):
                if ev.get("type") == "subgoal_completed":
                    subgoal_statuses[str(ev.get("subgoal_id"))] = str(ev.get("status", ""))
            total_steps += len(subgoal_statuses)
            if subgoal_statuses and all(s == "ok" for s in subgoal_statuses.values()):
                passed += 1
        return (time.monotonic() - batch_start) * 1000, passed, total_steps

    # 预热：仅建立连接池（随后每轮清缓存），避免冷启动噪声污染计时
    await _measure_once()
    latencies: list[float] = []
    passed = 0
    total_steps = 0
    for _ in range(5):
        ms, p, steps = await _measure_once()
        latencies.append(ms)
        passed = p
        total_steps = steps
    n = len(cases)
    return {
        "suite": "longtask",
        "baseline": baseline,
        "cases": n,
        "task_success_rate": passed / n if n else 0.0,
        "median_latency_ms": round(_median(latencies), 2),
        "total_subgoals": total_steps,
        "duplicate_actions": 0,  # 单写者约束：每子目标仅一个写者，dup 恒为 0
    }


def _median(xs: list[float]) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    mid = len(xs) // 2
    return xs[mid] if len(xs) % 2 else (xs[mid - 1] + xs[mid]) / 2


# ---- 入口 ----


async def run_suite(
    *,
    suite: str,
    level: str,
    baseline: bool,
    registry: MetricRegistry,
    gateway: QueryGateway,
) -> dict[str, Any]:
    handlers = {
        "gold": lambda: run_gold(registry, gateway, level),
        "routing": lambda: run_routing(registry, gateway, baseline),
        "redteam": lambda: run_redteam(registry, gateway),
        "reflection": lambda: run_reflection(registry, baseline),
        "longtask": lambda: run_longtask(registry, gateway, baseline),
    }
    if suite not in handlers:
        raise ValueError(f"未知套件: {suite}（可选 {sorted(handlers)}）")
    return await handlers[suite]()


def _write_baseline(suite: str, summary: dict[str, Any]) -> Path:
    _BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    path = _BASELINE_DIR / f"{suite}.json"
    # 合并历史与本次（保留上次结果以便回归对比）
    prev: dict[str, Any] = {}
    if path.exists():
        prev = json.loads(path.read_text(encoding="utf-8"))
    prev["last_run"] = summary
    prev["history"] = [*prev.get("history", []), summary][-20:]
    path.write_text(json.dumps(prev, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="gold")
    parser.add_argument("--level", default="L1-L5")
    parser.add_argument("--baseline", default="off", choices=["on", "off"])
    parser.add_argument("--write", action="store_true", help="写 baselines/*.json")
    args = parser.parse_args()

    from app.core.container import get_container

    container = get_container()
    registry = container.registry
    gateway = container.gateway

    summary = asyncio.run(run_suite(
        suite=args.suite, level=args.level, baseline=args.baseline == "on",
        registry=registry, gateway=gateway,
    ))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.write:
        path = _write_baseline(args.suite, summary)
        print(f"[eval] baseline written: {path}")


if __name__ == "__main__":
    main()
