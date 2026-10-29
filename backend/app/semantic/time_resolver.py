"""时间解析：自然语言时间 → 绝对半开区间 [start, end)，锚定快照日，确定性可复现。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from app.core.config import settings

# 快照锚定日：相对时间窗口（"最近 N 天"）以此为终点，保证评测跨日可复现
ANCHOR = date.fromisoformat(settings.snapshot_date)


@dataclass
class ResolvedTime:
    start_date: date
    end_date: date  # EXCLUSIVE（半开区间）
    granularity: str = "day"  # day | week | month | quarter | year
    compare: str | None = None  # prev_period | same_period_ly
    source: str = ""


def _month_bounds(y: int, m: int) -> tuple[date, date]:
    """返回 [当月首日, 下月首日)。"""
    nxt = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    return date(y, m, 1), nxt


def _quarter_bounds(y: int, q: int) -> tuple[date, date]:
    start_m = (q - 1) * 3 + 1
    end_m = start_m + 3
    nxt = date(y + 1, 1, 1) if end_m > 12 else date(y, end_m, 1)
    return date(y, start_m, 1), nxt


def _shift_months(d: date, n: int) -> date:
    y, m = d.year, d.month + n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    day = min(d.day, 28)
    return date(y, m, day)


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def resolve(text: str, anchor: date | None = None) -> ResolvedTime | None:
    """解析时间表达式，命中返回 ResolvedTime，未命中返回 None。"""
    a = anchor or ANCHOR
    t = text.strip()

    # 具体区间 "2026-09-01 到 2026-09-30" / "2026年9月1日至9月30日"
    m = re.search(
        r"(20\d{2})[-年/](\d{1,2})月?(\d{1,2})?日?.*?(到|至|~|-).*?"
        r"(20\d{2})[-年/](\d{1,2})月?(\d{1,2})?日?",
        t,
    )
    if m and m.group(3) and m.group(7):
        s = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        e = date(int(m.group(5)), int(m.group(6)), int(m.group(7)))
        return ResolvedTime(s, e, source="explicit_range")

    # 具体月份 "2026年9月" / "2026-09"
    m = re.search(r"(20\d{2})[-年/](\d{1,2})月?", t)
    if m and "到" not in t and "至" not in t:
        s, e = _month_bounds(int(m.group(1)), int(m.group(2)))
        return ResolvedTime(s, e, granularity="month", source="explicit_month")

    # 近 N 天 / 最近 N 天 / 过去 N 天
    m = re.search(r"(?:近|最近|过去|近(?:一|两|三|半)?)\s*(\d{1,3})\s*(?:天|日)", t)
    if m:
        n = int(m.group(1))
        s = a - timedelta(days=n - 1)
        return ResolvedTime(s, a + timedelta(days=1), source=f"recent_{n}_days")

    # 近 N 个月 / 近 N 月
    m = re.search(r"(?:近|最近|过去)\s*(\d{1,2})\s*个?月", t)
    if m:
        n = int(m.group(1))
        s = _shift_months(date(a.year, a.month, 1), -(n - 1))
        return ResolvedTime(s, _month_bounds(a.year, a.month)[1], granularity="month",
                            source=f"recent_{n}_months")

    # 近半年 / 近一年
    if "近半年" in t or "近6个月" in t:
        s = _shift_months(date(a.year, a.month, 1), -5)
        return ResolvedTime(s, _month_bounds(a.year, a.month)[1], granularity="month",
                            source="recent_6_months")
    if "近一年" in t or "近12个月" in t or "近1年" in t:
        s = _shift_months(date(a.year, a.month, 1), -11)
        return ResolvedTime(s, _month_bounds(a.year, a.month)[1], granularity="month",
                            source="recent_12_months")

    # 本月 / 上月（含环比/同比修饰）
    if "上月" in t or "上个月" in t:
        prev = _shift_months(date(a.year, a.month, 1), -1)
        s, e = _month_bounds(prev.year, prev.month)
        cmp = "prev_period" if "环比" in t else ("same_period_ly" if "同比" in t else None)
        return ResolvedTime(s, e, granularity="month", compare=cmp, source="last_month")
    if "本月" in t or "这个月" in t:
        s, e = _month_bounds(a.year, a.month)
        return ResolvedTime(s, e, granularity="month", source="this_month")

    # 上周 / 本周
    if "上周" in t or "上星期" in t:
        ws = _week_start(a) - timedelta(days=7)
        return ResolvedTime(ws, ws + timedelta(days=7), granularity="week", source="last_week")
    if "本周" in t or "这周" in t:
        ws = _week_start(a)
        return ResolvedTime(ws, ws + timedelta(days=7), granularity="week", source="this_week")

    # 上季度 / 本季度 / 去年
    if "上季度" in t or "上个季度" in t:
        q = (a.month - 1) // 3 + 1
        prev_q = q - 1 if q > 1 else 4
        py = a.year if q > 1 else a.year - 1
        s, e = _quarter_bounds(py, prev_q)
        return ResolvedTime(s, e, granularity="quarter", source="last_quarter")
    if "本季度" in t or "这个季度" in t:
        q = (a.month - 1) // 3 + 1
        s, e = _quarter_bounds(a.year, q)
        return ResolvedTime(s, e, granularity="quarter", source="this_quarter")
    if "去年" in t or "上年" in t:
        s, e = date(a.year - 1, 1, 1), date(a.year, 1, 1)
        return ResolvedTime(s, e, granularity="year", source="last_year")
    if "今年" in t or "本年" in t:
        s, e = date(a.year, 1, 1), date(a.year + 1, 1, 1)
        return ResolvedTime(s, e, granularity="year", source="this_year")

    # 季度 "Q3" / "2026Q3"
    m = re.search(r"(20\d{2})?\s*Q([1-4])", t, re.IGNORECASE)
    if m:
        y = int(m.group(1)) if m.group(1) else a.year
        q = int(m.group(2))
        s, e = _quarter_bounds(y, q)
        return ResolvedTime(s, e, granularity="quarter", source=f"Q{q}")

    # 昨天 / 今天
    if "昨天" in t:
        return ResolvedTime(a - timedelta(days=1), a, source="yesterday")
    if "今天" in t or "今日" in t:
        return ResolvedTime(a, a + timedelta(days=1), source="today")

    return None
