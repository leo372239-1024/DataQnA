"""数据库 schema：analytics 数仓（RLS）+ app 系统表。

幂等建表（CREATE TABLE IF NOT EXISTS）。RLS 策略在 analytics 表上强制执行租户隔离。
"""
from __future__ import annotations

ANALYTICS_SCHEMA = "analytics"
APP_SCHEMA = "app"

# ---- analytics 数仓表 ----

FACT_ORDER = f"""
CREATE SCHEMA IF NOT EXISTS {ANALYTICS_SCHEMA};
CREATE TABLE IF NOT EXISTS {ANALYTICS_SCHEMA}.fact_order (
    order_id        BIGINT PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    user_id         BIGINT NOT NULL,
    region_id       INT NOT NULL,
    province_id     INT NOT NULL,
    category_id     INT NOT NULL,
    sub_category_id INT NOT NULL,
    channel_id      INT NOT NULL,
    payment_id      INT NOT NULL,
    device_id       INT NOT NULL,
    tier_id         INT NOT NULL,
    order_seq       INT NOT NULL DEFAULT 1,
    is_new_user     BOOLEAN NOT NULL DEFAULT FALSE,
    status          TEXT NOT NULL,
    refund_status   TEXT NOT NULL DEFAULT 'NONE',
    pay_amount      NUMERIC(18,4) NOT NULL,
    gross_amount    NUMERIC(18,4) NOT NULL,
    refund_amount   NUMERIC(18,4) NOT NULL DEFAULT 0,
    freight_amount  NUMERIC(18,4) NOT NULL DEFAULT 0,
    coupon_amount   NUMERIC(18,4) NOT NULL DEFAULT 0,
    item_qty        INT NOT NULL DEFAULT 1,
    visit_cnt       INT NOT NULL DEFAULT 1,
    paid_at         DATE NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fact_order_paid_at ON {ANALYTICS_SCHEMA}.fact_order(paid_at);
CREATE INDEX IF NOT EXISTS ix_fact_order_tenant ON {ANALYTICS_SCHEMA}.fact_order(tenant_id);
"""

_DIM_TABLES = {
    "dim_region": "region_id INT PRIMARY KEY, province_id INT, region_name TEXT, province_name TEXT, city_name TEXT",
    "dim_category": "category_id INT PRIMARY KEY, sub_category_id INT, category_name TEXT, sub_category_name TEXT",
    "dim_channel": "channel_id INT PRIMARY KEY, channel_name TEXT",
    "dim_order_payment": "payment_id INT PRIMARY KEY, payment_name TEXT",
    "dim_device": "device_id INT PRIMARY KEY, device_name TEXT",
    "dim_user": "tier_id INT PRIMARY KEY, tier_name TEXT",
}

DIM_TABLES = "\n".join(
    f"CREATE TABLE IF NOT EXISTS {ANALYTICS_SCHEMA}.{name} ({cols});"
    for name, cols in _DIM_TABLES.items()
)

# RLS：分析表按 tenant_id 隔离（数据库层兜底）
_RLS_TABLES = ["fact_order"]
RLS_POLICIES = "\n".join(
    f"""
ALTER TABLE {ANALYTICS_SCHEMA}.{t} ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON {ANALYTICS_SCHEMA}.{t};
CREATE POLICY tenant_isolation ON {ANALYTICS_SCHEMA}.{t}
    USING (tenant_id = current_setting('app.tenant_id', true)::text);
"""
    for t in _RLS_TABLES
)

# ---- app 系统表 ----

APP_TABLES = f"""
CREATE SCHEMA IF NOT EXISTS {APP_SCHEMA};
CREATE TABLE IF NOT EXISTS {APP_SCHEMA}.users (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    username TEXT NOT NULL,
    roles TEXT[] NOT NULL DEFAULT '{{}}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS {APP_SCHEMA}.semantic_metric (
    id TEXT PRIMARY KEY,
    name_cn TEXT NOT NULL,
    aliases TEXT[] NOT NULL,
    type TEXT NOT NULL,
    expression TEXT,
    source_tables TEXT[] NOT NULL,
    default_time_col TEXT,
    filters TEXT[],
    numerator TEXT,
    denominator TEXT,
    unit TEXT,
    precision INT NOT NULL DEFAULT 2,
    caliber_cn TEXT NOT NULL,
    owner TEXT,
    version INT NOT NULL DEFAULT 1,
    tags TEXT[] NOT NULL DEFAULT '{{}}',
    risk_level TEXT NOT NULL DEFAULT 'low',
    semantic_version INT NOT NULL
);
CREATE TABLE IF NOT EXISTS {APP_SCHEMA}.semantic_dimension (
    id TEXT PRIMARY KEY,
    name_cn TEXT NOT NULL,
    table_name TEXT NOT NULL,
    key_column TEXT NOT NULL,
    value_column TEXT NOT NULL,
    join_sql TEXT NOT NULL,
    aliases TEXT[] NOT NULL,
    hierarchy TEXT[] NOT NULL,
    value_aliases JSONB NOT NULL DEFAULT '{{}}',
    cardinality_estimate INT NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS {APP_SCHEMA}.asset (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    aliases TEXT[] NOT NULL,
    domains TEXT[] NOT NULL,
    capability TEXT NOT NULL,
    params_schema JSONB NOT NULL,
    permissions TEXT[] NOT NULL,
    risk TEXT NOT NULL DEFAULT 'low',
    version INT NOT NULL DEFAULT 1,
    deprecated BOOLEAN NOT NULL DEFAULT FALSE,
    requires_confirmation BOOLEAN NOT NULL DEFAULT FALSE,
    success_rate REAL NOT NULL DEFAULT 1.0,
    avg_latency_ms REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS {APP_SCHEMA}.episode (
    id BIGSERIAL PRIMARY KEY,
    trace_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    question TEXT NOT NULL,
    intent JSONB,
    outcome TEXT,
    failure_code TEXT,
    semantic_version INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS {APP_SCHEMA}.span (
    id BIGSERIAL PRIMARY KEY,
    trace_id TEXT NOT NULL,
    span_id TEXT NOT NULL,
    parent_span_id TEXT,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    duration_ms REAL,
    token_in INT,
    token_out INT,
    model TEXT,
    scanned_bytes BIGINT,
    failure_code TEXT,
    asset_id TEXT,
    semantic_version INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS {APP_SCHEMA}.semantic_memory (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    fact TEXT NOT NULL,
    embedding vector(256),
    source_episode_id BIGINT,
    confidence REAL NOT NULL DEFAULT 0.5,
    applied_count INT NOT NULL DEFAULT 0,
    helped_count INT NOT NULL DEFAULT 0,
    hurt_count INT NOT NULL DEFAULT 0,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS {APP_SCHEMA}.audit_log (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    user_id TEXT,
    action TEXT NOT NULL,
    tool TEXT,
    params_masked JSONB,
    result_code TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

# 只读角色授权（表创建后执行）
GRANTS = """
GRANT USAGE ON SCHEMA analytics TO analytics_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO analytics_ro;
"""

ALL_DDL = "\n".join([FACT_ORDER, DIM_TABLES, RLS_POLICIES, APP_TABLES, GRANTS])
