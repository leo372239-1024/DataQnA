"""种子入口：建表 → 灌数仓数据 → 加载指标注册表 → 写系统表。

用法: uv run python -m app.seed [--start 2025-07-01] [--end 2026-09-30] [--per-day 300]
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date
from typing import Any

import asyncpg
import yaml

from app.core.config import settings
from app.seed import data
from app.seed.schema import ALL_DDL


def _dsn(url: str) -> str:
    # asyncpg 接受 postgresql://，去掉 +asyncpg 即可
    return url.replace("+asyncpg", "")


def _load_registry() -> dict[str, Any]:
    import pathlib

    path = pathlib.Path(__file__).parent / "metrics" / "registry.yaml"
    with open(path, encoding="utf-8") as f:
        return dict(yaml.safe_load(f))


async def seed(start: date, end: date, per_day: int) -> None:
    conn = await asyncpg.connect(_dsn(settings.database_url))

    # 1. 建表
    await conn.execute(ALL_DDL)

    # 2. 维度数据
    await conn.executemany(
        "INSERT INTO analytics.dim_region (region_id, province_id, region_name, province_name, city_name) "
        "VALUES ($1,$2,$3,$4,$5) ON CONFLICT (region_id) DO NOTHING",
        data.region_rows(),
    )
    await conn.executemany(
        "INSERT INTO analytics.dim_category (category_id, sub_category_id, category_name, sub_category_name) "
        "VALUES ($1,$2,$3,$4) ON CONFLICT (category_id) DO NOTHING",
        data.category_rows(),
    )
    await conn.executemany(
        "INSERT INTO analytics.dim_channel (channel_id, channel_name) VALUES ($1,$2) ON CONFLICT DO NOTHING",
        data.channel_rows(),
    )
    await conn.executemany(
        "INSERT INTO analytics.dim_order_payment (payment_id, payment_name) VALUES ($1,$2) ON CONFLICT DO NOTHING",
        data.payment_rows(),
    )
    await conn.executemany(
        "INSERT INTO analytics.dim_device (device_id, device_name) VALUES ($1,$2) ON CONFLICT DO NOTHING",
        data.device_rows(),
    )
    await conn.executemany(
        "INSERT INTO analytics.dim_user (tier_id, tier_name) VALUES ($1,$2) ON CONFLICT DO NOTHING",
        data.tier_rows(),
    )

    # 3. 订单数据（幂等：先清空再灌）
    await conn.execute("TRUNCATE analytics.fact_order")
    orders = data.generate_orders(start=start, end=end, per_day=per_day)
    rows = [
        (
            o.order_id, o.tenant_id, o.user_id, o.region_id, o.province_id, o.category_id,
            o.sub_category_id, o.channel_id, o.payment_id, o.device_id, o.tier_id,
            o.order_seq, o.is_new_user, o.status, o.refund_status,
            o.pay_amount, o.gross_amount, o.refund_amount, o.freight_amount,
            o.coupon_amount, o.item_qty, o.visit_cnt, o.paid_at,
        )
        for o in orders
    ]
    # 分批插入，避免单条语句过大
    batch = 5000
    for i in range(0, len(rows), batch):
        await conn.executemany(
            "INSERT INTO analytics.fact_order "
            "(order_id, tenant_id, user_id, region_id, province_id, category_id, "
            " sub_category_id, channel_id, payment_id, device_id, tier_id, "
            " order_seq, is_new_user, status, refund_status, "
            " pay_amount, gross_amount, refund_amount, freight_amount, coupon_amount, "
            " item_qty, visit_cnt, paid_at) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23)",
            rows[i : i + batch],
        )

    # 4. 指标/维度注册表 → 系统表
    registry = _load_registry()
    sv = registry["semantic_version"]
    await conn.execute("DELETE FROM app.semantic_metric")
    for m in registry["metrics"]:
        await conn.execute(
            "INSERT INTO app.semantic_metric "
            "(id, name_cn, aliases, type, expression, source_tables, default_time_col, filters, "
            " numerator, denominator, unit, precision, caliber_cn, owner, version, tags, risk_level, semantic_version) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18)",
            m["id"], m["name_cn"], m.get("aliases", []), m["type"], m.get("expression"),
            m.get("source_tables", []), m.get("default_time_col"), m.get("filters", []),
            m.get("numerator"), m.get("denominator"), m.get("unit"), m.get("precision", 2),
            m.get("caliber_cn", ""), m.get("owner"), m.get("version", 1),
            m.get("tags", []), m.get("risk_level", "low"), sv,
        )
    await conn.execute("DELETE FROM app.semantic_dimension")
    for d in registry["dimensions"]:
        await conn.execute(
            "INSERT INTO app.semantic_dimension "
            "(id, name_cn, table_name, key_column, value_column, join_sql, aliases, hierarchy, value_aliases, cardinality_estimate) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)",
            d["id"], d["name_cn"], d["table"], d["key_column"], d["value_column"], d["join_sql"],
            d.get("aliases", []), d.get("hierarchy", []),
            json.dumps(d.get("value_aliases", {}), ensure_ascii=False),
            d.get("cardinality_estimate", 0),
        )

    # 5. 测试用户
    await conn.execute(
        "INSERT INTO app.users (tenant_id, username, roles) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING",
        "t1", "demo", ["analyst"],
    )

    await conn.close()
    print(f"[seed] done: {len(orders)} orders, {len(registry['metrics'])} metrics, "
          f"{len(registry['dimensions'])} dimensions")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2025-07-01")
    parser.add_argument("--end", default="2026-09-30")
    parser.add_argument("--per-day", type=int, default=300)
    args = parser.parse_args()
    asyncio.run(seed(date.fromisoformat(args.start), date.fromisoformat(args.end), args.per_day))


if __name__ == "__main__":
    main()
