"""三层记忆领域模型：Episodic / Semantic / Procedural（Lesson）。

- Episode 只存结果摘要与失败码，绝不存原始工具 payload（见 reflection 的隐私边界）。
- SemanticMemory 带 tenant_id 与向量，用于跨任务复用的事实/偏好。
- Lesson 是可撤回的程序性经验，带 applied/helped/hurt 计数用于「有效才持久」验证。
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from app.memory.failure_codes import validate_failure_code

# 语义记忆准入阈值（spec：低于此值进隔离区，绝不自动应用）
ADMIT_THRESHOLD = 0.75


def _now() -> datetime:
    return datetime.now(UTC)


class Episode(BaseModel):
    """一次任务运行的情景记忆。"""

    id: str
    tenant_id: str
    question: str
    intent_level: str = ""
    outcome: Literal["success", "failure"]
    failure_code: str | None = None  # 失败必填（9 类之一）
    # 只存摘要，不存原始 payload
    subgoal_summary: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)

    @field_validator("failure_code")
    @classmethod
    def _code_valid(cls, v: str | None) -> str | None:
        validate_failure_code(v)
        return v

    @field_validator("failure_code")
    @classmethod
    def _failure_requires_code(cls, v: str | None, info: ValidationInfo) -> str | None:
        if info.data.get("outcome") == "failure" and v is None:
            raise ValueError("失败的 episode 必须携带 9 类失败码")
        return v


class SemanticMemory(BaseModel):
    """语义记忆：可复用的去重事实/偏好，租户隔离 + 向量化。"""

    id: str
    tenant_id: str
    content: str
    embedding: list[float] = Field(default_factory=list)
    confidence: float = 1.0
    status: Literal["quarantined", "admitted", "revoked"] = "quarantined"
    evidence_episode_id: str | None = None
    applies_to: str | None = None  # 关联的 asset_id / metric_id
    created_at: datetime = Field(default_factory=_now)


class Lesson(BaseModel):
    """程序性经验（写回资产/指标注册表），带有效性计数，可撤销。"""

    id: str
    tenant_id: str
    lesson: str
    applies_to: str | None = None  # asset_id / metric_id
    action: Literal[
        "add_alias", "enrich_description", "fix_schema", "router_penalty", "other"
    ] = "other"
    confidence: float = 0.0
    status: Literal["quarantined", "admitted", "revoked"] = "quarantined"
    evidence_episode_id: str | None = None
    admitted_at: datetime | None = None
    applied_count: int = 0
    helped_count: int = 0
    hurt_count: int = 0
    created_at: datetime = Field(default_factory=_now)

    @property
    def net_effect(self) -> int:
        return self.helped_count - self.hurt_count
