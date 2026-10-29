"""确定性提示词护栏：意图分类前对用户提问做恶意意图预筛。

针对「只读分析 agent」的威胁面，拦截三类高风险直接注入/越权意图：
1. 指令注入 —— 覆盖系统指令、要求删除/写库等破坏性操作
2. 越权 —— 跨租户读取、以管理员身份执行、绕过审批
3. 诱导臆造 —— 虚构指标、导出 PII 等

注意：这是「廉价优先」的确定性第一道防线（spec §2 第一/二/三层为结构性隔离，
本模块补充直接指令注入的确定性预筛）。命中即阻断，绝不进入意图分类/编排。
"""
from __future__ import annotations

# 阻断关键词组：命中任一即判定恶意意图（返回命中词组，供审计记录）。
# 关键词均为「破坏性动词 / 越权意图」的强信号，正常问数不会命中。
_BLOCK_PATTERNS: tuple[tuple[str, str], ...] = (
    # 指令注入 / 破坏性操作
    ("忽略之前的指令", "INSTRUCTION_INJECTION"),
    ("忽略指令", "INSTRUCTION_INJECTION"),
    ("忽略以上", "INSTRUCTION_INJECTION"),
    ("删除所有", "DESTRUCTIVE_ACTION"),
    ("删除订单", "DESTRUCTIVE_ACTION"),
    ("DROP TABLE", "SQL_INJECTION"),
    ("DELETE FROM", "SQL_INJECTION"),
    ("TRUNCATE", "SQL_INJECTION"),
    ("直接写数据库", "DESTRUCTIVE_ACTION"),
    ("写数据库", "DESTRUCTIVE_ACTION"),
    # 越权 / 提权
    ("其他租户", "CROSS_TENANT"),
    ("别的租户", "CROSS_TENANT"),
    ("管理员身份", "PRIVILEGE_ESCALATION"),
    ("管理员权限", "PRIVILEGE_ESCALATION"),
    ("绕过权限", "PRIVILEGE_ESCALATION"),
    ("绕过审批", "PRIVILEGE_ESCALATION"),
    ("任意操作", "PRIVILEGE_ESCALATION"),
    ("竞对公司的", "CROSS_ORGANIZATION"),
    ("竞争对手", "CROSS_ORGANIZATION"),
    # 诱导臆造 / PII 导出
    ("虚构一个不存在的指标", "FABRICATION"),
    ("编造一个指标", "FABRICATION"),
    ("导出所有用户的手机号", "PII_EXPORT"),
    ("导出用户手机号", "PII_EXPORT"),
    ("所有用户的手机号", "PII_EXPORT"),
    ("以管理员身份", "PRIVILEGE_ESCALATION"),
)


def detect_unsafe_prompt(question: str) -> str | None:
    """返回第一个命中的阻断码；未命中返回 None。"""
    upper = question.upper()
    for pattern, code in _BLOCK_PATTERNS:
        if pattern.upper() in upper:
            return code
    return None
