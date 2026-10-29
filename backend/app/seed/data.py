"""数仓种子数据生成：可复现（固定随机种子），埋入 3 类口径陷阱。

陷阱 1（率值）：品类订单量差 ~100×，且退款率差异大 → 品类退款率算术平均 ≠ 全局退款率。
陷阱 2（口径）：gmv_paid（已支付含运费不含退款） vs gmv_gross（含退款/取消），运费/优惠券是否计入。
陷阱 3（时间）：订单跨月/跨年边界，同比依赖去年同期数据。
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

# ---- 维度定义 ----

REGIONS = [
    ("华东", [("沪", "上海"), ("苏", "江苏"), ("浙", "浙江")]),
    ("华南", [("粤", "广东"), ("桂", "广西"), ("琼", "海南")]),
    ("华北", [("京", "北京"), ("津", "天津"), ("冀", "河北")]),
    ("西南", [("川", "四川"), ("渝", "重庆"), ("滇", "云南")]),
    ("西北", [("陕", "陕西"), ("甘", "甘肃")]),
    ("东北", [("辽", "辽宁"), ("吉", "吉林")]),
    ("华中", [("鄂", "湖北"), ("湘", "湖南")]),
]

# (category_name, sub_categories, weight, refund_rate) — weight 制造订单量 100× 差异
CATEGORIES = [
    ("手机数码", ["手机", "电脑", "配件"], 3000, 0.010),
    ("家用电器", ["大家电", "小家电"], 2000, 0.020),
    ("服饰鞋包", ["男装", "女装", "鞋靴"], 1500, 0.080),
    ("美妆个护", ["护肤", "彩妆"], 1200, 0.060),
    ("食品生鲜", ["零食", "生鲜"], 1200, 0.050),
    ("家居家装", ["家具", "家纺"], 800, 0.070),
    ("母婴玩具", ["奶粉", "玩具"], 600, 0.040),
    ("运动户外", ["运动鞋", "户外装备"], 500, 0.055),
    ("图书文娱", ["图书", "影音"], 300, 0.090),
    ("汽车用品", ["车载", "维修"], 150, 0.120),
    ("宠物用品", ["宠粮", "用品"], 30, 0.250),
    ("珠宝腕表", ["珠宝", "腕表"], 20, 0.180),
]

CHANNELS = ["线上", "线下", "分销", "直播", "自营"]
PAYMENTS = ["支付宝", "微信支付", "银行卡", "货到付款", "白条", "其他"]
DEVICES = ["移动端", "PC端", "小程序", "H5"]
TIERS = ["普通", "银卡", "金卡", "白金", "黑金"]

# 品类权重总和（用于归一化）
_TOTAL_WEIGHT = sum(c[2] for c in CATEGORIES)
_CUM = []
_acc = 0
for c in CATEGORIES:
    _acc += c[2]
    _CUM.append(_acc)


def _pick_category(rng: random.Random) -> int:
    x = rng.randint(0, _TOTAL_WEIGHT - 1)
    for i, acc in enumerate(_CUM):
        if x < acc:
            return i
    return len(CATEGORIES) - 1


@dataclass
class Order:
    order_id: int
    tenant_id: str
    user_id: int
    region_id: int
    province_id: int
    category_id: int
    sub_category_id: int
    channel_id: int
    payment_id: int
    device_id: int
    tier_id: int
    order_seq: int
    is_new_user: bool
    status: str
    refund_status: str
    pay_amount: float
    gross_amount: float
    refund_amount: float
    freight_amount: float
    coupon_amount: float
    item_qty: int
    visit_cnt: int
    paid_at: date


def _money(rng: random.Random, lo: float, hi: float) -> float:
    return round(rng.uniform(lo, hi), 2)


def generate_orders(
    start: date, end: date, per_day: int = 300, seed: int = 42, tenant_id: str = "t1"
) -> list[Order]:
    """生成 [start, end) 的订单。固定种子保证可复现。"""
    rng = random.Random(seed)
    orders: list[Order] = []
    order_id = 1
    # 用户池：预生成一批用户，用于复购/新客标记
    user_pool: dict[int, int] = {}  # user_id -> 已下单次数
    next_user = 1

    d = start
    while d < end:
        n = per_day + rng.randint(-40, 40)  # 每日轻微波动
        for _ in range(max(1, n)):
            cat_idx = _pick_category(rng)
            _, subs, _w, refund_rate = CATEGORIES[cat_idx]
            sub_idx = rng.randrange(len(subs))

            # 用户：多数老客，少数新客
            if rng.random() < 0.08 or not user_pool:
                uid = next_user
                next_user += 1
                user_pool[uid] = 0
                is_new = True
            else:
                uid = rng.choice(list(user_pool.keys()))
                is_new = False
            user_pool[uid] += 1
            order_seq = user_pool[uid]

            region_idx = rng.randrange(len(REGIONS))
            prov_idx = rng.randrange(len(REGIONS[region_idx][1]))

            # 金额（按品类大致定价）
            base = {0: (2000, 8000), 1: (800, 5000), 2: (100, 800), 3: (50, 400),
                    4: (30, 200), 5: (100, 2000), 6: (80, 600), 7: (100, 900),
                    8: (20, 100), 9: (50, 500), 10: (30, 300), 11: (1000, 20000)}[cat_idx]
            pay = _money(rng, *base)
            freight = _money(rng, 0, 30) if pay < 2000 else 0
            coupon = _money(rng, 0, pay * 0.15)

            # 退款（按品类退款率）
            refund = round(pay, 2) if rng.random() < refund_rate else 0.0
            refund_status = "REFUNDED" if refund > 0 else "NONE"

            # 状态：绝大多数成功，少量取消
            r = rng.random()
            if r < 0.02:
                status = "CANCELLED"
            elif r < 0.06:
                status = "UNPAID"
            else:
                status = rng.choice(["PAID", "SHIPPED", "DONE"])

            gross = round(pay + refund + freight + coupon, 2)

            orders.append(Order(
                order_id=order_id, tenant_id=tenant_id, user_id=uid,
                region_id=region_idx + 1, province_id=region_idx * 100 + prov_idx + 1,
                category_id=cat_idx + 1, sub_category_id=cat_idx * 10 + sub_idx + 1,
                channel_id=rng.randrange(len(CHANNELS)) + 1,
                payment_id=rng.randrange(len(PAYMENTS)) + 1,
                device_id=rng.randrange(len(DEVICES)) + 1,
                tier_id=rng.randrange(len(TIERS)) + 1,
                order_seq=order_seq, is_new_user=is_new, status=status,
                refund_status=refund_status,
                pay_amount=pay, gross_amount=gross, refund_amount=refund,
                freight_amount=freight, coupon_amount=coupon,
                item_qty=rng.randint(1, 4), visit_cnt=rng.randint(1, 8),
                paid_at=d,
            ))
            order_id += 1
        d += timedelta(days=1)
    return orders


# ---- 维度数据 ----

def region_rows() -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    for ri, (rname, provs) in enumerate(REGIONS):
        for pi, (_pabbr, pname) in enumerate(provs):
            rows.append((ri + 1, ri * 100 + pi + 1, rname, pname, pname))
    return rows


def category_rows() -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    for ci, (cname, subs, _w, _r) in enumerate(CATEGORIES):
        for si, sname in enumerate(subs):
            rows.append((ci + 1, ci * 10 + si + 1, cname, sname))
    return rows


def channel_rows() -> list[tuple[Any, ...]]:
    return [(i + 1, n) for i, n in enumerate(CHANNELS)]


def payment_rows() -> list[tuple[Any, ...]]:
    return [(i + 1, n) for i, n in enumerate(PAYMENTS)]


def device_rows() -> list[tuple[Any, ...]]:
    return [(i + 1, n) for i, n in enumerate(DEVICES)]


def tier_rows() -> list[tuple[Any, ...]]:
    return [(i + 1, n) for i, n in enumerate(TIERS)]
