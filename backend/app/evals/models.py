"""评测领域模型：统一的用例 schema 覆盖 gold/routing/redteam/reflection 四类套件。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvalCase:
    """一条评测用例。不同套件使用不同字段子集。"""

    id: str
    suite: str  # gold | routing | redteam | reflection
    level: str  # L1..L5（routing/redteam 用 level 标注难度但不参与分型）
    question: str
    # gold 期望
    expected_metric_ids: list[str] = field(default_factory=list)
    expected_dims: list[str] = field(default_factory=list)
    expected_compare: str | None = None  # prev_period | same_period_ly | None
    expected_time_start: str | None = None  # ISO date
    expected_time_end: str | None = None
    tolerance: float = 0.01
    caliber_check: str = ""  # 口径披露须包含的子串
    traps: list[str] = field(default_factory=list)  # rate | caliber | time
    # routing 期望
    expected_asset_id: str | None = None
    caller_roles: list[str] = field(default_factory=list)
    # redteam 期望
    should_block: bool = False
    # reflection 期望
    expect_retry_success: bool = False
    learn_alias: str | None = None  # 反思循环应学习的缺失别名


@dataclass
class CaseResult:
    """单条用例的评测结果。"""

    case_id: str
    passed: bool
    failure_code: str | None = None  # 9 类失败码之一；成功为 None
    detail: dict[str, Any] = field(default_factory=dict)
