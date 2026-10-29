"""实体链接：把用户提及 → 注册指标/维度，歧义反问，绝不猜。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings
from app.semantic.embedding import cosine, embed
from app.semantic.models import MetricDef
from app.semantic.registry import MetricRegistry

# 词形归一：去标点/空白、小写、去常见后缀
_SUFFIXES = ("率", "额", "数", "量", "值", "占比", "金额")


@dataclass
class Candidate:
    metric: MetricDef
    score: float
    source: str  # alias | lexical | vector


@dataclass
class MetricLink:
    status: str  # RESOLVED | AMBIGUOUS | NO_MATCH
    metric: MetricDef | None = None
    confidence: float = 0.0
    candidates: list[Candidate] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


def _normalize(text: str) -> str:
    t = re.sub(r"[\s，。、（）()%％]+", "", text).lower()
    while t and any(t.endswith(s) for s in _SUFFIXES if len(s) <= len(t)):
        for s in _SUFFIXES:
            if t.endswith(s) and len(t) > len(s):
                t = t[: -len(s)]
                break
        else:
            break
    return t


def link_metric(registry: MetricRegistry, mention: str) -> MetricLink:
    """三级链接：精确别名 → 词形归一 → 向量召回。歧义则反问。"""
    m = mention.strip()
    if not m:
        return MetricLink(status="NO_MATCH", evidence={"recall": [], "mention": m})

    # Stage 1: 精确别名
    exact_id = registry.alias_to_metric(m)
    if exact_id:
        metric = registry.get_metric(exact_id)
        return MetricLink(
            status="RESOLVED", metric=metric, confidence=0.95,
            candidates=[Candidate(metric, 0.95, "alias")],
            evidence={"matched_alias": m, "stage": "alias"},
        )

    # Stage 2: 词形归一（对指标名/别名的归一化比对）
    norm = _normalize(m)
    for metric in registry.metrics:
        for a in [metric.name_cn, *metric.aliases]:
            if norm and _normalize(a) == norm:
                return MetricLink(
                    status="RESOLVED", metric=metric, confidence=0.85,
                    candidates=[Candidate(metric, 0.85, "lexical")],
                    evidence={"matched_lexical": a, "stage": "lexical"},
                )

    # Stage 3: 向量召回
    qv = embed(m)
    scored: list[Candidate] = []
    for metric in registry.metrics:
        # 用 name_cn + aliases + caliber 拼接做语义
        text = " ".join([metric.name_cn, *metric.aliases])
        s = cosine(qv, embed(text))
        scored.append(Candidate(metric, round(s, 4), "vector"))
    scored.sort(key=lambda c: c.score, reverse=True)

    top1 = scored[0] if scored else None
    if top1 is None or top1.score < settings.accept_threshold:
        return MetricLink(
            status="NO_MATCH", candidates=scored[:5],
            evidence={"recall": [(c.metric.id, c.score) for c in scored[:5]], "stage": "vector"},
        )

    top2 = scored[1] if len(scored) > 1 else None
    if top2 and (top1.score - top2.score) < settings.ambiguity_margin:
        return MetricLink(
            status="AMBIGUOUS", candidates=scored[:5],
            evidence={"stage": "vector", "top1": top1.metric.id, "top2": top2.metric.id},
        )

    return MetricLink(
        status="RESOLVED", metric=top1.metric, confidence=top1.score,
        candidates=scored[:5],
        evidence={"recall": [(c.metric.id, c.score) for c in scored[:5]], "stage": "vector"},
    )
