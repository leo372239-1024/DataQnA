"""编排器：intent → plan → 执行 DAG（并行独立子目标）→ 归因/报告 → 合成答案。

以 async generator 产出事件流（SSE 直接消费）。
"""
from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

from app.agent.intent import classify_intent
from app.agent.planner import plan
from app.agent.state import AgentState, Subgoal, SubgoalResult
from app.core.logging import get_logger
from app.dsl.compiler import SecurityContext, compile_sql
from app.dsl.models import QueryDSL
from app.dsl.validators import check_cost, check_result, check_semantic, check_static
from app.guardrails.prompt_guard import detect_unsafe_prompt
from app.observability.span import Tracer
from app.query.gateway import QueryGateway
from app.semantic.models import MetricDef
from app.semantic.registry import MetricRegistry

logger = get_logger()


@dataclass
class AnswerEnvelope:
    question: str
    level: str
    value: float | None = None
    rows: list[dict[str, Any]] = field(default_factory=list)
    caliber: str = ""
    sql: str = ""
    lineage: list[dict[str, Any]] = field(default_factory=list)
    chart: dict[str, Any] | None = None
    conclusion: str = ""
    subgoal_trace: list[dict[str, Any]] = field(default_factory=list)
    clarification: dict[str, Any] | None = None


def _topo_order(subgoals: list[Subgoal], dep: dict[str, list[str]]) -> list[list[str]]:
    """拓扑排序 + 独立子目标并行批次。返回 [[ids...], [ids...], ...]"""
    indeg = {s.id: 0 for s in subgoals}
    children: dict[str, list[str]] = {s.id: [] for s in subgoals}
    for child, parents in dep.items():
        indeg[child] = len(parents)
        for p in parents:
            children[p].append(child)

    batches: list[list[str]] = []
    ready = deque(sorted([s.id for s in subgoals if indeg[s.id] == 0]))
    while ready:
        batch = list(ready)
        ready.clear()
        batches.append(batch)
        for nid in batch:
            for c in children.get(nid, []):
                indeg[c] -= 1
                if indeg[c] == 0:
                    ready.append(c)
    return batches


class Orchestrator:
    def __init__(self, registry: MetricRegistry, gateway: QueryGateway) -> None:
        self.registry = registry
        self.gateway = gateway

    async def run(self, question: str, ctx: SecurityContext, roles_hash: str = "",
                  tracer: Tracer | None = None,
                  sequential: bool = False) -> AsyncGenerator[dict[str, Any], None]:
        state = AgentState(question=question, tenant_id=ctx.tenant_id)
        try:
            # 0. 确定性提示词护栏（直接注入/越权/臆造意图，先于一切）
            block_code = detect_unsafe_prompt(question)
            if block_code is not None:
                yield {"type": "blocked", "code": block_code,
                       "detail": "该请求包含高风险意图，已被安全护栏拦截"}
                yield {"type": "done"}
                return

            # 1. intent
            intent_span = tracer.start("intent", "classify_intent") if tracer else None
            intent = classify_intent(question, self.registry)
            if intent_span is not None:
                intent_span.finish()
            state.intent = intent
            yield {"type": "intent_classified", "level": intent.level,
                   "metrics": intent.metric_ids, "dimensions": intent.dimension_ids,
                   "time": [intent.start_date.isoformat() if intent.start_date else None,
                            intent.end_date.isoformat() if intent.end_date else None],
                   "evidence": intent.evidence}

            if not intent.metric_ids:
                clarify = {
                    "reason": "NO_MATCH",
                    "detail": "未能识别到已注册指标，请换一种说法（如：上月 GMV、各品类退款率）",
                }
                yield {"type": "clarification", **clarify}
                yield {"type": "error",
                       "error": {"code": "NO_MATCH", "detail": clarify["detail"]}}
                yield {"type": "done"}
                return

            # 2. plan
            plan_span = tracer.start("plan", "plan_dag") if tracer else None
            p = plan(intent, self.registry)
            if plan_span is not None:
                plan_span.finish()
            state.plan = p
            yield {"type": "plan_created", "subgoals": [
                {"id": s.id, "name": s.name, "kind": s.kind, "deps": s.deps} for s in p.subgoals]}

            # 3. execute DAG
            batches = _topo_order(p.subgoals, p.dependency)
            for batch in batches:
                for sid in batch:
                    sg = next(s for s in p.subgoals if s.id == sid)
                    yield {"type": "subgoal_started", "subgoal_id": sid,
                           "name": sg.name, "kind": sg.kind}
                if sequential:
                    # 基线模式：顺序执行（用于长时程任务 A/B 对照）
                    for sid in batch:
                        sg = next(s for s in p.subgoals if s.id == sid)
                        r = await self._exec_subgoal(sg, ctx, roles_hash, state, tracer)
                        state.results[sid] = r
                        sg.result = r
                        yield {"type": "subgoal_completed", "subgoal_id": sid,
                               "status": r.status}
                    continue
                tasks = []
                for sid in batch:
                    sg = next(s for s in p.subgoals if s.id == sid)
                    tasks.append(self._exec_subgoal(sg, ctx, roles_hash, state, tracer))
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for sg_id, raw in zip(batch, results, strict=True):
                    if isinstance(raw, BaseException):
                        state.results[sg_id] = SubgoalResult(subgoal_id=sg_id, status="failed",
                                                             failure_code="TOOL_MISUSE",
                                                             evidence={"error": str(raw)})
                    else:
                        state.results[sg_id] = raw
                    sg = next(s for s in p.subgoals if s.id == sg_id)
                    sg.result = state.results[sg_id]
                    yield {"type": "subgoal_completed", "subgoal_id": sg_id,
                           "status": state.results[sg_id].status}

            # 4. synthesize
            envelope = self._synthesize(state, ctx)
            yield {"type": "answer", "level": envelope.level, "value": envelope.value,
                   "rows": envelope.rows, "caliber": envelope.caliber, "sql": envelope.sql,
                   "lineage": envelope.lineage, "chart": envelope.chart,
                   "conclusion": envelope.conclusion}
            yield {"type": "done"}
        except Exception as e:  # noqa: BLE001
            logger.error("orchestrate_failed", error=str(e))
            yield {"type": "error", "error": {"code": "INTERNAL", "detail": str(e)}}
            yield {"type": "done"}

    async def _exec_subgoal(self, sg: Subgoal, ctx: SecurityContext, roles_hash: str,
                            state: AgentState,
                            tracer: Tracer | None = None) -> SubgoalResult:
        if sg.kind == "attribution":
            return self._compute_attribution(state)
        if sg.kind == "report":
            return SubgoalResult(subgoal_id=sg.id, status="ok", evidence={"kind": "report"})
        # query 类
        dsl = sg.dsl
        if dsl is None:
            return SubgoalResult(subgoal_id=sg.id, status="failed", failure_code="TOOL_MISUSE",
                                 evidence={"error": "子目标缺少 DSL"})
        return await self._exec_query(sg.id, dsl, ctx, roles_hash, tracer)

    async def _exec_query(self, sg_id: str, dsl: QueryDSL, ctx: SecurityContext,
                          roles_hash: str,
                          tracer: Tracer | None = None) -> SubgoalResult:
        # 四道校验（静态/语义/成本在编译前后）
        v = check_static(dsl, self.registry, ctx) + check_semantic(dsl, self.registry, ctx)
        blocking = [x for x in v if x.blocking]
        if blocking:
            return SubgoalResult(subgoal_id=sg_id, status="failed",
                                 failure_code=blocking[0].failure_code,
                                 evidence={"violation": blocking[0].detail})
        compiled = compile_sql(dsl, self.registry, ctx)
        cost_v = check_cost(dsl, compiled, ctx)
        sql_span = tracer.start("sql_exec", f"exec_{sg_id}") if tracer else None
        try:
            result = await self.gateway.execute(
                compiled, ctx, self.registry.semantic_version, roles_hash)
        except Exception as e:  # noqa: BLE001
            if sql_span is not None:
                sql_span.finish(status="error", failure_code="TOOL_MISUSE")
            return SubgoalResult(subgoal_id=sg_id, status="failed", failure_code="TOOL_MISUSE",
                                 evidence={"error": str(e)})
        if sql_span is not None:
            sql_span.scanned_bytes = result.scanned_bytes
            sql_span.meta = {"rows": len(result.rows), "cache_hit": result.cache_hit}
            sql_span.finish()
        result_v = check_result(result.rows, dsl)
        metric = self.registry.get_metric(dsl.metrics[0].metric_id)
        return SubgoalResult(
            subgoal_id=sg_id, status="ok", rows=result.rows, columns=result.columns,
            dsl=dsl, sql=compiled.sql, scanned_bytes=result.scanned_bytes,
            latency_ms=result.latency_ms,
            evidence={"caliber": metric.caliber_cn, "cost_violations": [x.detail for x in cost_v],
                      "result_notes": [x.detail for x in result_v]},
        )

    def _compute_attribution(self, state: AgentState) -> SubgoalResult:
        """两因素精确分解（对称 Shapley 分解，交互项均摊，加总严格等于总变化）。

        全局率值 = Σ rate_i × share_i，share_i 为分母占比。
        贡献 = 率值效应 + 权重效应，其中：
          率值效应  = Δrate × mean(share_cur, share_base)
          权重效应  = Δshare × mean(rate_cur, rate_base)
        二者加总恒等于 Δ全局率值（无残差）。
        """
        cur = state.results.get("q1")
        base = state.results.get("q2")
        if not cur or not base or cur.status != "ok" or base.status != "ok":
            return SubgoalResult(subgoal_id="q3", status="failed", failure_code="CONTEXT_LOSS",
                                 evidence={"detail": "归因依赖的查询未完成"})
        dim = (state.plan.intent.dimension_ids[0]
               if state.plan and state.plan.intent.dimension_ids else "category")

        def rows_to_map(rows: list[dict[str, Any]], dim: str) -> dict[str, dict[str, float]]:
            return {str(r[dim]): {"rate": float(r["m0"] or 0),
                                  "weight": float(r["m1"] or 0)} for r in rows}

        cur_m = rows_to_map(cur.rows, dim)
        base_m = rows_to_map(base.rows, dim)

        cur_total_w = sum(x["weight"] for x in cur_m.values()) or 1
        base_total_w = sum(x["weight"] for x in base_m.values()) or 1
        cur_rate = sum(x["rate"] * x["weight"] for x in cur_m.values()) / cur_total_w
        base_rate = sum(x["rate"] * x["weight"] for x in base_m.values()) / base_total_w
        total_change = cur_rate - base_rate

        contributions: list[dict[str, Any]] = []
        for k in sorted(set(cur_m) | set(base_m)):
            r_cur = cur_m.get(k, {}).get("rate", 0.0)
            r_base = base_m.get(k, {}).get("rate", 0.0)
            w_cur_n = cur_m.get(k, {}).get("weight", 0.0) / cur_total_w
            w_base_n = base_m.get(k, {}).get("weight", 0.0) / base_total_w
            rate_effect = (r_cur - r_base) * (w_cur_n + w_base_n) / 2.0
            weight_effect = (w_cur_n - w_base_n) * (r_cur + r_base) / 2.0
            contrib = rate_effect + weight_effect
            contributions.append({
                "dimension_value": k,
                "contribution": round(contrib, 6),
                "rate_effect": round(rate_effect, 6),
                "weight_effect": round(weight_effect, 6),
                "rate_cur": round(r_cur, 6),
                "rate_base": round(r_base, 6),
            })
        contributions.sort(key=lambda x: abs(x["contribution"]), reverse=True)

        return SubgoalResult(
            subgoal_id="q3", status="ok",
            rows=contributions,
            evidence={"total_change": round(total_change, 6), "cur_rate": round(cur_rate, 6),
                      "base_rate": round(base_rate, 6),
                      "contribution_sum": round(sum(c["contribution"] for c in contributions), 6)},
        )

    def _synthesize(self, state: AgentState, ctx: SecurityContext) -> AnswerEnvelope:
        intent = state.intent
        if intent is None:
            return AnswerEnvelope(question=state.question, level="L1")
        env = AnswerEnvelope(question=state.question, level=intent.level)
        env.subgoal_trace = [{"id": k, "status": v.status, "failure_code": v.failure_code}
                             for k, v in state.results.items()]

        if intent.level == "L4":
            attr = state.results.get("q3")
            if attr and attr.status == "ok":
                ev = attr.evidence
                env.value = ev["total_change"]
                env.rows = attr.rows
                env.chart = {"type": "waterfall", "title": "贡献度分解",
                             "items": attr.rows, "total_change": ev["total_change"]}
                main = self.registry.get_metric(intent.metric_ids[0])
                env.caliber = main.caliber_cn
                env.lineage = [{"metric_id": main.id, "name_cn": main.name_cn,
                                "version": main.version}]
                env.conclusion = self._attribution_conclusion(main, ev, attr.rows)
                if state.results.get("q1"):
                    env.sql = state.results["q1"].sql
                return env

        if intent.level == "L3":
            q1 = state.results.get("q1")
            q2 = state.results.get("q2")
            if q1 and q2 and q1.status == "ok" and q2.status == "ok" and q1.rows and q2.rows:
                cur = float(q1.rows[0].get("m0") or 0)
                base = float(q2.rows[0].get("m0") or 0)
                delta = cur - base
                pct = (delta / base) if base else 0.0
                env.value = cur
                env.rows = [{"current": cur, "baseline": base, "delta": delta, "delta_pct": pct}]
                env.sql = q1.sql
                main = self.registry.get_metric(intent.metric_ids[0])
                env.caliber = main.caliber_cn
                env.lineage = [{"metric_id": main.id, "name_cn": main.name_cn,
                                "version": main.version}]
                env.chart = {"type": "compare", "current": cur, "baseline": base,
                             "delta": delta, "delta_pct": pct}
                env.conclusion = (f"当前期 {cur:,.2f}，对比期 {base:,.2f}，"
                                  f"变化 {delta:+,.2f}（{pct:+.2%}）")
                return env

        if intent.level == "L5":
            # 多指标报告：合并逐指标查询结果，生成结构化报告
            metric_rows: list[dict[str, Any]] = []
            lineage: list[dict[str, Any]] = []
            all_sql: list[str] = []
            for mid in intent.metric_ids:
                main = self.registry.get_metric(mid)
                lineage.append({"metric_id": mid, "name_cn": main.name_cn,
                                "version": main.version})
                found = False
                for res in state.results.values():
                    if (res.status == "ok" and res.dsl and res.dsl.metrics
                            and res.dsl.metrics[0].metric_id == mid and res.rows):
                        row = res.rows[0].get("m0")
                        metric_rows.append({"metric_id": mid, "name_cn": main.name_cn,
                                            "value": row})
                        all_sql.append(res.sql)
                        found = True
                        break
                if not found:
                    metric_rows.append({"metric_id": mid, "name_cn": main.name_cn,
                                        "value": None})
            env.rows = metric_rows
            env.lineage = lineage
            env.sql = "\n;\n".join(all_sql)
            env.caliber = "；".join(
                f"{self.registry.get_metric(m).name_cn}:{self.registry.get_metric(m).caliber_cn}"
                for m in intent.metric_ids)
            env.chart = {"type": "report", "items": metric_rows}
            env.value = None  # 报告无单一数值
            env.conclusion = (f"本报告包含 {len(metric_rows)} 项指标："
                              + "、".join(f"{r['name_cn']}={r['value']}" for r in metric_rows))
            return env

        # L1-L3：取主查询结果
        q = state.results.get("q1")
        if q and q.status == "ok" and q.rows:
            env.rows = q.rows
            env.sql = q.sql
            main = self.registry.get_metric(intent.metric_ids[0])
            env.caliber = main.caliber_cn
            env.lineage = [{"metric_id": main.id, "name_cn": main.name_cn, "version": main.version}]
            if not intent.dimension_ids and len(q.rows) == 1:
                env.value = float(q.rows[0]["m0"]) if q.rows[0].get("m0") is not None else None
            elif intent.compare:
                env.chart = {"type": "compare", "items": q.rows}
            elif intent.dimension_ids:
                env.chart = {"type": "bar", "dimension": intent.dimension_ids[0], "items": q.rows}
        return env

    def _attribution_conclusion(self, metric: MetricDef, ev: dict[str, Any],
                                contributions: list[dict[str, Any]]) -> str:
        if not contributions:
            return "无数据，无法归因。"
        top = contributions[:3]
        total = ev["total_change"]
        direction = "上升" if total > 0 else "下降"
        parts = [f"{c['dimension_value']}（贡献 {c['contribution']:+.4f}）" for c in top]
        return (f"「{metric.name_cn}」{direction} {abs(total):.4f}，主要由 "
                + "、".join(parts) + " 驱动。")
