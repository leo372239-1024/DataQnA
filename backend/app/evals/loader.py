"""评测用例加载器：从 YAML 读取，解析为 EvalCase。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.evals.models import EvalCase

# 评测数据根目录：backend/evals/
EVALS_ROOT = Path(__file__).resolve().parent.parent.parent / "evals"

# 套件 → 目录映射（spec：gold/routing/redteam/reflection）
_SUITE_DIRS = {
    "gold": "gold",
    "routing": "routing",
    "redteam": "redteam",
    "reflection": "reflection",
}


def _to_case(suite: str, raw: dict[str, Any]) -> EvalCase:
    return EvalCase(
        id=str(raw["id"]),
        suite=suite,
        level=str(raw.get("level", "L1")),
        question=str(raw["question"]),
        expected_metric_ids=list(raw.get("expected_metric_ids", [])),
        expected_dims=list(raw.get("expected_dims", [])),
        expected_compare=raw.get("expected_compare"),
        expected_time_start=raw.get("expected_time_start"),
        expected_time_end=raw.get("expected_time_end"),
        tolerance=float(raw.get("tolerance", 0.01)),
        caliber_check=str(raw.get("caliber_check", "")),
        traps=list(raw.get("traps", [])),
        expected_asset_id=raw.get("expected_asset_id"),
        caller_roles=list(raw.get("caller_roles", ["analyst"])),
        should_block=bool(raw.get("should_block", False)),
        expect_retry_success=bool(raw.get("expect_retry_success", False)),
        learn_alias=raw.get("learn_alias"),
    )


def load_suite(suite: str, root: Path | None = None) -> list[EvalCase]:
    """加载一个套件的全部用例（该目录下所有 *.yaml）。"""
    root = root or EVALS_ROOT
    if suite not in _SUITE_DIRS:
        raise ValueError(f"未知评测套件: {suite}")
    dir_path = root / _SUITE_DIRS[suite]
    if not dir_path.exists():
        return []
    cases: list[EvalCase] = []
    for f in sorted(dir_path.glob("*.yaml")):
        with open(f, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        items = raw.get("cases", raw if isinstance(raw, list) else [])
        for item in items:
            cases.append(_to_case(suite, item))
    return cases


def _expand_levels(spec: str) -> set[str]:
    """把 'L1-L5' / 'L1,L3' 展开为级别集合。"""
    levels: set[str] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            lo, hi = lo.strip(), hi.strip()
            if lo.startswith("L") and hi.startswith("L"):
                for n in range(int(lo[1:]), int(hi[1:]) + 1):
                    levels.add(f"L{n}")
            else:
                levels.add(part)
        else:
            levels.add(part)
    return levels


def load_cases(suite: str, level: str = "", root: Path | None = None) -> list[EvalCase]:
    """加载套件并按 level 过滤（level 为空则全部；支持 'L1-L5' 范围与 'L1,L3' 枚举）。"""
    cases = load_suite(suite, root)
    if not level:
        return cases
    levels = _expand_levels(level)
    return [c for c in cases if c.level in levels]
