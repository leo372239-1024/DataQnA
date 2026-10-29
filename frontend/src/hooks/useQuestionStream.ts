/** SSE 流式消费 hook：把 AgentEvent 流折叠为 UI 状态（纯 reducer + 状态机）。 */
import { useEffect, useMemo, useReducer, useRef } from "react";
import { streamQuestion } from "../api/questions";
import type { AgentEvent, AnswerOut, LineageNode, SubgoalPlan } from "../api/schemas";

export type StreamStatus = "idle" | "running" | "done" | "error";

export interface SubgoalView {
  id: string;
  name: string;
  kind: string;
  status: "running" | "ok" | "failed";
}

export interface StreamState {
  status: StreamStatus;
  level: string | null;
  metrics: string[];
  dimensions: string[];
  subgoals: SubgoalView[];
  answer: AnswerOut | null;
  clarification: string | null;
  blocked: { code: string; detail: string } | null;
  error: string | null;
  traceId: string | null;
}

export type StreamAction =
  | { type: "reset" }
  | { type: "start" }
  | { type: "status"; level?: string; metrics?: string[]; dimensions?: string[]; subgoals?: SubgoalPlan[] }
  | { type: "subgoal"; subgoal_id: string; name?: string; kind?: string; status?: string }
  | { type: "answer"; answer: AnswerOut }
  | { type: "clarification"; detail: string }
  | { type: "blocked"; code: string; detail: string }
  | { type: "error"; detail: string }
  | { type: "done"; traceId?: string };

export const initialState: StreamState = {
  status: "idle",
  level: null,
  metrics: [],
  dimensions: [],
  subgoals: [],
  answer: null,
  clarification: null,
  blocked: null,
  error: null,
  traceId: null,
};

function toAnswer(lineage: LineageNode[] | undefined): AnswerOut["lineage"] {
  return lineage ?? [];
}

export function streamReducer(state: StreamState, action: StreamAction): StreamState {
  switch (action.type) {
    case "reset":
      return initialState;
    case "start":
      return { ...initialState, status: "running" };
    case "status": {
      // status 事件可能携带意图（level/metrics/dimensions）或计划（subgoals）
      let subgoals = state.subgoals;
      if (action.subgoals && action.subgoals.length > 0) {
        subgoals = action.subgoals.map((s) => ({
          id: s.id,
          name: s.name,
          kind: s.kind,
          status: "running" as const,
        }));
      }
      return {
        ...state,
        level: action.level ?? state.level,
        metrics: action.metrics ?? state.metrics,
        dimensions: action.dimensions ?? state.dimensions,
        subgoals,
      };
    }
    case "subgoal": {
      const next = state.subgoals.map((s) =>
        s.id === action.subgoal_id
          ? { ...s, status: action.status === "ok" ? "ok" : action.status === "failed" ? "failed" : s.status, name: action.name ?? s.name, kind: action.kind ?? s.kind }
          : s,
      );
      // 尚未出现在列表中的（防御）追加
      const known = new Set(next.map((s) => s.id));
      if (!known.has(action.subgoal_id)) {
        next.push({
          id: action.subgoal_id,
          name: action.name ?? action.subgoal_id,
          kind: action.kind ?? "",
          status: action.status === "ok" ? "ok" : action.status === "failed" ? "failed" : "running",
        });
      }
      return { ...state, subgoals: next };
    }
    case "answer":
      return { ...state, answer: { ...action.answer, lineage: toAnswer(action.answer.lineage) } };
    case "clarification":
      return { ...state, clarification: action.detail };
    case "blocked":
      return { ...state, blocked: { code: action.code, detail: action.detail } };
    case "error":
      return { ...state, status: "error", error: action.detail };
    case "done":
      return { ...state, status: "done", traceId: action.traceId ?? state.traceId };
    default: {
      const _exhaustive: never = action;
      void _exhaustive;
      return state;
    }
  }
}

/** 把已 Zod 校验的 AgentEvent 映射为 reducer action。 */
export function eventToAction(ev: AgentEvent): StreamAction {
  switch (ev.type) {
    case "status":
      return {
        type: "status",
        level: ev.level,
        metrics: ev.metrics,
        dimensions: ev.dimensions,
        subgoals: ev.subgoals,
      };
    case "subgoal":
      return {
        type: "subgoal",
        subgoal_id: ev.subgoal_id,
        name: ev.name,
        kind: ev.kind,
        status: ev.status,
      };
    case "answer":
      return {
        type: "answer",
        answer: {
          question_id: "",
          level: ev.level,
          value: ev.value,
          rows: ev.rows,
          caliber: ev.caliber,
          sql: ev.sql,
          lineage: ev.lineage,
          chart: ev.chart ?? null,
          conclusion: ev.conclusion,
          subgoal_trace: [],
          trace_id: null,
        },
      };
    case "clarification":
      return { type: "clarification", detail: ev.detail ?? ev.reason ?? "信息不足，请补充说明" };
    case "blocked":
      return { type: "blocked", code: ev.code ?? "BLOCKED", detail: ev.detail ?? "请求已被拦截" };
    case "error":
      return { type: "error", detail: ev.error.detail ?? ev.error.code };
    case "done":
      return { type: "done", traceId: ev.trace_id };
    default: {
      const _exhaustive: never = ev;
      void _exhaustive;
      return { type: "reset" };
    }
  }
}

/** 订阅某 question 的 SSE 流。questionId 为空时 idle。 */
export function useQuestionStream(questionId: string | null): StreamState {
  const [state, dispatch] = useReducer(streamReducer, initialState);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!questionId) {
      dispatch({ type: "reset" });
      return;
    }
    const controller = new AbortController();
    abortRef.current = controller;
    dispatch({ type: "start" });
    let cancelled = false;

    (async () => {
      try {
        for await (const ev of streamQuestion(questionId, controller.signal)) {
          if (cancelled) break;
          dispatch(eventToAction(ev));
        }
      } catch (e) {
        if (!cancelled && !controller.signal.aborted) {
          dispatch({ type: "error", detail: e instanceof Error ? e.message : "流式请求失败" });
        }
      }
    })();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [questionId]);

  return useMemo(() => state, [state]);
}
