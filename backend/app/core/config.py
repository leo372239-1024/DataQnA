"""应用配置：pydantic-settings 单源，环境变量驱动。"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DATAQNA_", extra="ignore")

    app_name: str = "DataQnA"
    api_prefix: str = "/api/v1"
    debug: bool = False

    # 数据库：app 连接可写系统 schema，analytics 连接只读（结构性防写）
    database_url: str = "postgresql+asyncpg://dataqna:dataqna@localhost:5432/dataqna"
    analytics_url: str = "postgresql+asyncpg://analytics_ro:analytics_ro@localhost:5432/dataqna"
    redis_url: str = "redis://localhost:6379/0"

    # LLM 网关
    llm_provider: str = "stub"  # stub | openai_compat
    llm_model: str = "local-stub"
    llm_api_key: str = ""
    llm_base_url: str = ""

    # 语义层阈值
    ambiguity_margin: float = 0.15
    accept_threshold: float = 0.85
    route_margin: float = 0.12

    # 编排与熔断
    max_replans: int = 2
    max_steps: int = 12
    max_tokens_per_run: int = 200_000
    max_wall_clock_seconds: int = 300
    duplicate_action_threshold: int = 2

    # 上下文压缩
    context_budget_ratio: float = 0.7  # 触发压缩的窗口负载比例
    context_target_ratio: float = 0.55  # 压缩后目标负载
    sliding_window_turns: int = 5

    # 评测
    snapshot_date: str = "2026-09-30"  # 数仓快照锚定日，保证可复现

    # 成本计量
    scan_price_per_gb_cny: float = 0.01


settings = Settings()
