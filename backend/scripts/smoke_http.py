"""DataQnA 部署态端到端冒烟：经 HTTP 提交 L1-L5 问题，校验 SSE 事件流闭合。

默认经前端 nginx 代理（http://127.0.0.1:5173），也可直接指向后端。

用法:
  python scripts/smoke_http.py [base_url]
退出码: 全部 PASS 为 0, 任一 FAIL 为 1。
"""
from __future__ import annotations

import json
import sys
import urllib.request

CASES: list[tuple[str, str]] = [
    ("L1", "上月GMV是多少"),
    ("L2", "近30天各品类的退款率"),
    ("L3", "上月退款率环比"),
    ("L4", "为什么退款率环比上升了，是哪个大区导致的"),
    ("L5", "本月GMV、订单数和退款率"),
]


def post_question(base: str, q: str) -> str:
    payload = json.dumps({
        "question": q,
        "tenant_id": "t1",
        "user_id": "demo",
        "roles": ["analyst"],
        "timezone": "Asia/Shanghai",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/v1/questions", data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["question_id"]


def stream_question(base: str, qid: str) -> tuple[list[str], str]:
    types: list[str] = []
    answer: object | None = None
    with urllib.request.urlopen(f"{base}/api/v1/questions/{qid}/stream", timeout=90) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data: "):
                continue
            d = json.loads(line[6:])
            t = d.get("type", "")
            types.append(t)
            if t == "answer":
                answer = d.get("value")
            if t == "error":
                detail = d.get("error", {}).get("detail", "")
                return types, f"error: {detail}"
    return types, f"answer={answer!r}"


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5173"
    print(f"== DataQnA 部署态冒烟（L1-L5）via {base} ==", flush=True)
    failed = 0
    for level, q in CASES:
        try:
            qid = post_question(base, q)
            types, summary = stream_question(base, qid)
            ok = "answer" in types and "done" in types
            if not ok:
                failed += 1
            print(f"[{level}] {'PASS' if ok else 'FAIL'} :: {q!r} -> {summary}", flush=True)
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"[{level}] FAIL :: {q!r} -> {type(e).__name__}: {e}", flush=True)
    print(f"== 冒烟完成: {len(CASES) - failed}/{len(CASES)} PASS ==", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
