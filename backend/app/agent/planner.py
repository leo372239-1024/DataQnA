"""混合分解 planner：程序化骨架（按 L1–L5）→ 子目标 DAG + 依赖。"""
from __future__ import annotations

from datetime import date

from app.agent.state import IntentFrame, Plan, Subgoal
from app.dsl.models import (
    DimensionRef,
    MetricRef,
    QueryDSL,
    TimeWindow,
)
from app.semantic.registry import MetricRegistry


def _build_dsl(
    intent: IntentFrame,
    registry: MetricRegistry,
    *,
    compare: bool = False,
    dimensions: bool = True,
) -> QueryDSL:
    metrics = [MetricRef(metric_id=mid, semantic_version=registry.semantic_version)
               for mid in intent.metric_ids]
    dims = [DimensionRef(dimension_id=did) for did in intent.dimension_ids] if dimensions else []
    return QueryDSL(
        metrics=metrics,
        dimensions=dims,
        time=TimeWindow(
            start_date=intent.start_date,
            end_date=intent.end_date,
            granularity=intent.granularity,
            compare=intent.compare if compare else None,
        ),
        semantic_version=registry.semantic_version,
    )


def _prev_window(intent: IntentFrame) -> tuple[date, date]:
    """返回上一周期（同长度）的 [start, end)。"""
    s, e = intent.start_date, intent.end_date
    if s is None or e is None:
        raise ValueError("intent 缺少时间窗口，无法计算上一周期")
    span = e - s
    return s - span, s


def _comparison_window(intent: IntentFrame) -> tuple[date, date]:
    """按 compare 返回对比窗口 [start, end)。"""
    s, e = intent.start_date, intent.end_date
    if s is None or e is None:
        raise ValueError("intent 缺少时间窗口，无法计算对比期")
    if intent.compare == "same_period_ly":
        try:
            return s.replace(year=s.year - 1), e.replace(year=e.year - 1)
        except ValueError:
            return s.replace(year=s.year - 1, day=28), e.replace(year=e.year - 1, day=28)
    return _prev_window(intent)  # prev_period


def plan(intent: IntentFrame, registry: MetricRegistry, plan_id: str = "p1") -> Plan:
    """程序化分解：按意图级别生成子目标 DAG。"""
    subgoals: list[Subgoal] = []
    dep: dict[str, list[str]] = {}

    if intent.level == "L1":
        subgoals.append(Subgoal(id="q1", name="查询指标", kind="query",
                                dsl=_build_dsl(intent, registry, dimensions=False)))

    elif intent.level == "L2":
        subgoals.append(Subgoal(id="q1", name="多维聚合", kind="query",
                                dsl=_build_dsl(intent, registry)))

    elif intent.level == "L3":
        # 同环比：当前期 + 对比期，独立并行
        cur = _build_dsl(intent, registry, compare=False)
        subgoals.append(Subgoal(id="q1", name="当前期", kind="query", dsl=cur))
        base = _build_dsl(intent, registry, compare=False)
        bs, be = _comparison_window(intent)
        base.time.start_date, base.time.end_date = bs, be
        subgoals.append(Subgoal(id="q2", name="对比期", kind="query", dsl=base))

    elif intent.level == "L4":
        # 归因：当前期 vs 上一期（同长度），按维度分解贡献。
        # 权重指标 = 主指标的分母（ratio）或订单数（additive），用于两因素分解。
        main = registry.get_metric(intent.metric_ids[0])
        if main.type == "ratio" and main.denominator is not None:
            weight = main.denominator
        else:
            weight = "order_cnt"
        attr_metric_ids = [main.id, weight]
        # 归因必须有分组维度：未显式指定时默认按品类（category）分解贡献
        attr_dims = intent.dimension_ids or ["category"]

        def _attr_dsl(metrics: list[str]) -> QueryDSL:
            return QueryDSL(
                metrics=[MetricRef(metric_id=mid, semantic_version=registry.semantic_version)
                         for mid in metrics],
                dimensions=[DimensionRef(dimension_id=did) for did in attr_dims],
                time=TimeWindow(start_date=intent.start_date, end_date=intent.end_date),
                semantic_version=registry.semantic_version,
            )

        subgoals.append(Subgoal(id="q1", name="取当前期", kind="query",
                                dsl=_attr_dsl(attr_metric_ids)))
        ps, pe = _prev_window(intent)
        base = _attr_dsl(attr_metric_ids)
        base.time.start_date, base.time.end_date = ps, pe
        subgoals.append(Subgoal(id="q2", name="取对比期", kind="query", dsl=base))
        subgoals.append(Subgoal(id="q3", name="计算贡献度", kind="attribution", deps=["q1", "q2"]))
        dep = {"q3": ["q1", "q2"]}

    elif intent.level == "L5":
        # 多指标报告：逐指标分解为独立查询子目标（可并行），再汇总结论。
        # 长时程任务的「实时分解 + 并行编排」即体现在此：N 个指标 → N 个并行子目标。
        query_ids: list[str] = []
        for i, mid in enumerate(intent.metric_ids, start=1):
            dsl = _build_dsl(intent, registry, compare=False)
            dsl.metrics = [MetricRef(metric_id=mid, semantic_version=registry.semantic_version)]
            qid = f"q{i}"
            query_ids.append(qid)
            subgoals.append(Subgoal(id=qid, name=f"查询{mid}", kind="query", dsl=dsl))
        report_id = f"q{len(query_ids) + 1}"
        subgoals.append(Subgoal(id=report_id, name="生成结论", kind="report",
                                deps=query_ids))
        dep = {report_id: query_ids}

    return Plan(plan_id=plan_id, intent=intent, subgoals=subgoals, dependency=dep)
