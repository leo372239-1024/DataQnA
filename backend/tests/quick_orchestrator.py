"""编排器端到端验证：L1–L4 全链路。"""
import asyncio
import sys

sys.path.insert(0, ".")

from app.agent.orchestrator import Orchestrator
from app.dsl.compiler import SecurityContext
from app.query.gateway import QueryGateway
from app.semantic.registry import MetricRegistry

QUESTIONS = [
    "上月 GMV 是多少",                    # L1
    "各品类的成交金额",                    # L2
    "上月退款率环比是多少",                 # L3
    "为什么退款率环比上升了",              # L4 归因
]


async def run_one(orch, gw, reg, ctx, q):
    print(f"\n{'='*60}\nQ: {q}")
    async for ev in orch.run(q, ctx, roles_hash="r"):
        t = ev["type"]
        if t == "intent_classified":
            print(f"  intent: {ev['level']} metrics={ev['metrics']} dims={ev['dimensions']}")
        elif t == "plan_created":
            print(f"  plan: {[s['name'] for s in ev['subgoals']]}")
        elif t == "subgoal_completed":
            print(f"  subgoal {ev['subgoal_id']}: {ev['status']}")
        elif t == "answer":
            print(f"  ANSWER value={ev['value']}")
            print(f"  caliber: {ev['caliber']}")
            if ev['chart']:
                print(f"  chart: {ev['chart']['type']}")
            if ev['conclusion']:
                print(f"  conclusion: {ev['conclusion']}")
            if ev['rows'] and len(ev['rows']) <= 5:
                print(f"  rows: {ev['rows']}")
        elif t == "clarification":
            print(f"  CLARIFY: {ev['detail']}")
        elif t == "error":
            print(f"  ERROR: {ev['error']}")


async def main():
    reg = MetricRegistry.from_yaml("app/seed/metrics/registry.yaml")
    gw = QueryGateway()
    orch = Orchestrator(reg, gw)
    ctx = SecurityContext(tenant_id="t1")
    for q in QUESTIONS:
        await run_one(orch, gw, reg, ctx, q)


asyncio.run(main())
