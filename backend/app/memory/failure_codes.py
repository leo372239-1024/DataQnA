"""9 类失败码分类法 —— 生产 bad-case 与评测 bad-case 共用同一词汇表。

任何一层的失败都必须打上恰好一个码；自由文本只能伴随码，不能替代码。
"""
from __future__ import annotations

# 码 -> 含义（与 spec/memory-and-reflection.md 一致）
FAILURE_CODES: dict[str, str] = {
    "NO_MATCH": "实体/指标/工具未找到",
    "METRIC_AMBIG": "两个候选过于接近",
    "CONTEXT_LOSS": "早期结果在窗口中被丢弃",
    "TOOL_MISUSE": "选错工具或参数错误",
    "MULTI_TURN_DRIFT": "多轮间计划漂移",
    "HALLUCINATED_CALIBER": "LLM 臆造口径定义",
    "OVER_BLOCK": "护栏误拦截了合法请求",
    "RATE_TRAP": "比率指标聚合错误",
    "COST_OVERFLOW": "超出预算/扫描阈值",
}

# 各码对应的典型「写回修复」动作（供反思模块确定性抽取）
CODE_TO_FIX: dict[str, str] = {
    "NO_MATCH": "注册别名 / 新增指标",
    "METRIC_AMBIG": "锐化描述、拆分别名",
    "CONTEXT_LOSS": "提高压缩阈值、更早遮蔽",
    "TOOL_MISUSE": "补充工具描述 / 修正参数 schema",
    "MULTI_TURN_DRIFT": "新增骨架步骤、收紧重规划",
    "HALLUCINATED_CALIBER": "冻结口径到注册表，禁止 LLM 行文",
    "OVER_BLOCK": "调阈值、记录误拦",
    "RATE_TRAP": "核查编译器是否被绕过",
    "COST_OVERFLOW": "裁剪分区、加时间边界提示",
}


def is_valid_failure_code(code: str | None) -> bool:
    """成功（None）或合法失败码为 True；任意自由文本失败码为 False。"""
    return code is None or code in FAILURE_CODES


def validate_failure_code(code: str | None) -> None:
    if not is_valid_failure_code(code):
        raise ValueError(f"非法失败码: {code!r}（必须来自 9 类分类法或为 None）")
