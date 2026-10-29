"""确定性意图理解：自然语言 → IntentFrame（L1–L5 分级 + 指标/维度/时间/归因/环比）。"""
from __future__ import annotations

import datetime as _dt
from typing import Literal

from app.agent.state import IntentFrame
from app.core.config import settings
from app.semantic.registry import MetricRegistry
from app.semantic.time_resolver import ResolvedTime, resolve

_ATTRIBUTION_KW = ("为什么", "原因", "归因", "怎么回事", "导致", "哪些因素", "贡献")
_COMPARE_KW = {"环比": "prev_period", "同比": "same_period_ly"}

_Level = Literal["L1", "L2", "L3", "L4", "L5"]


def _greedy_extract(question: str, candidates: list[tuple[str, str]]) -> list[str]:
    """最长别名优先 + 重叠剔除：避免「退款」误命中「退款率」。"""
    hits: list[tuple[str, str, int, int]] = []
    for owner, cand in candidates:
        if len(cand) >= 2:
            pos = question.find(cand)
            if pos >= 0:
                hits.append((owner, cand, pos, pos + len(cand)))
    hits.sort(key=lambda h: (-len(h[1]), h[2]))
    chosen: list[tuple[str, int]] = []
    occupied: list[tuple[int, int]] = []
    for owner, _cand, s, e in hits:
        if any(not (e <= os or s >= oe) for os, oe in occupied):
            continue
        chosen.append((owner, s))
        occupied.append((s, e))
    chosen.sort(key=lambda x: x[1])
    return [owner for owner, _ in chosen]


def _extract_metrics(question: str, registry: MetricRegistry) -> list[str]:
    cands = [(m.id, c) for m in registry.metrics for c in [m.name_cn, *m.aliases]]
    return _greedy_extract(question, cands)


def _extract_dimensions(question: str, registry: MetricRegistry) -> list[str]:
    cands = [(d.id, c) for d in registry.dimensions for c in [d.name_cn, *d.aliases]]
    return _greedy_extract(question, cands)


def _classify_level(
    metric_ids: list[str], dimension_ids: list[str], compare: str | None, attribution: bool
) -> _Level:
    if attribution:
        return "L4"
    if len(metric_ids) >= 2:
        return "L5"  # 多指标报告
    if metric_ids and compare:
        return "L3"  # 单指标同环比
    if metric_ids and dimension_ids:
        return "L2"
    return "L1"


def _default_time() -> ResolvedTime:
    anchor = _dt.date.fromisoformat(settings.snapshot_date)
    return ResolvedTime(anchor - _dt.timedelta(days=29), anchor + _dt.timedelta(days=1),
                        source="default_recent_30")


def _last_month() -> ResolvedTime:
    """上月（完整自然月）窗口，供「环比/同比」未显式指定时间时使用。"""
    anchor = _dt.date.fromisoformat(settings.snapshot_date)
    y, m = anchor.year, anchor.month - 1
    if m == 0:
        y, m = y - 1, 12
    start = _dt.date(y, m, 1)
    end = _dt.date(y + 1, 1, 1) if m == 12 else _dt.date(y, m + 1, 1)
    return ResolvedTime(start, end, granularity="month", source="last_month_default")


def classify_intent(question: str, registry: MetricRegistry) -> IntentFrame:
    """确定性意图理解。未命中关键要素时给出 evidence 供上层澄清。"""
    compare: str | None = None
    for kw, op in _COMPARE_KW.items():
        if kw in question:
            compare = op
            break

    resolved = resolve(question)
    # 环比/同比语义天然基于「月」，未指定时间时默认上月；否则近 30 天
    t = (_last_month() if compare else _default_time()) if resolved is None else resolved

    attribution = any(k in question for k in _ATTRIBUTION_KW)
    metric_ids = _extract_metrics(question, registry)
    dimension_ids = _extract_dimensions(question, registry)

    level = _classify_level(metric_ids, dimension_ids, compare, attribution)

    return IntentFrame(
        level=level,
        metric_ids=metric_ids,
        dimension_ids=dimension_ids,
        start_date=t.start_date,
        end_date=t.end_date,
        granularity=t.granularity,
        compare=compare or t.compare,
        attribution=attribution,
        raw_question=question,
        evidence={
            "time_source": t.source,
            "metric_mentions": metric_ids,
            "dimension_mentions": dimension_ids,
            "compare_kw": compare,
            "attribution_kw": attribution,
        },
    )
