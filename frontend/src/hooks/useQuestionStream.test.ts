import { describe, expect, it } from "vitest";
import { initialState, streamReducer, eventToAction } from "./useQuestionStream";
import type { AgentEvent } from "../api/schemas";

describe("streamReducer", () => {
  it("start 重置为 running", () => {
    const s = streamReducer(initialState, { type: "start" });
    expect(s.status).toBe("running");
  });

  it("status 事件携带计划时初始化子目标", () => {
    const s = streamReducer(initialState, {
      type: "status",
      level: "L5",
      subgoals: [
        { id: "q1", name: "查询gmv_paid", kind: "query", deps: [] },
        { id: "q2", name: "查询order_cnt", kind: "query", deps: [] },
      ],
    });
    expect(s.level).toBe("L5");
    expect(s.subgoals).toHaveLength(2);
  });

  it("subgoal_completed 更新状态为 ok", () => {
    let s = streamReducer(initialState, {
      type: "status",
      subgoals: [{ id: "q1", name: "查询", kind: "query", deps: [] }],
    });
    s = streamReducer(s, { type: "subgoal", subgoal_id: "q1", status: "ok" });
    expect(s.subgoals[0]?.status).toBe("ok");
  });

  it("done 事件设置 traceId 与状态", () => {
    const s = streamReducer(initialState, { type: "done", traceId: "abc123" });
    expect(s.status).toBe("done");
    expect(s.traceId).toBe("abc123");
  });

  it("exhaustive switch：未知事件走 never 分支不崩溃", () => {
    const fake = { type: "impossible" } as unknown as AgentEvent;
    const s = eventToAction(fake);
    expect(s.type).toBe("reset");
  });
});
