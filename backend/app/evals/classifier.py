"""评测失败打标：把每条失败归因到 9 类失败码之一（与 memory/failure_codes 同词汇表）。"""
from __future__ import annotations

from dataclasses import dataclass

from app.memory.failure_codes import FAILURE_CODES, is_valid_failure_code


@dataclass
class FailureStat:
    code: str
    count: int


def classify_failure(reason: str, default: str = "TOOL_MISUSE") -> str:
    """把评测失败原因映射到 9 类失败码。未知原因回退 default（仍须合法）。"""
    mapping = {
        "level_mismatch": "TOOL_MISUSE",
        "metric_mismatch": "NO_MATCH",
        "dim_mismatch": "NO_MATCH",
        "compare_mismatch": "TOOL_MISUSE",
        "time_mismatch": "TOOL_MISUSE",
        "empty_result": "NO_MATCH",
        "invalid_sql": "TOOL_MISUSE",
        "caliber_mismatch": "HALLUCINATED_CALIBER",
        "lineage_missing": "CONTEXT_LOSS",
        "route_mismatch": "TOOL_MISUSE",
        "not_blocked": "OVER_BLOCK",
        "blocked_legit": "OVER_BLOCK",
        "rate_trap": "RATE_TRAP",
    }
    code = mapping.get(reason, default)
    return code if is_valid_failure_code(code) else default


def group_failures(failure_codes: list[str | None]) -> dict[str, int]:
    """按失败码聚合计数（失败码为 None 的成功不计入）。"""
    stats: dict[str, int] = {}
    for code in failure_codes:
        if code is None:
            continue
        stats[code] = stats.get(code, 0) + 1
    return stats


def failure_breakdown(failure_codes: list[str | None]) -> list[FailureStat]:
    """返回按计数降序的失败码分布，用于报告「74% EX 为什么」。"""
    grouped = group_failures(failure_codes)
    ordered = sorted(grouped.items(), key=lambda kv: (-kv[1], kv[0]))
    return [FailureStat(code=code, count=cnt) for code, cnt in ordered]


ALL_CODES = list(FAILURE_CODES.keys())
