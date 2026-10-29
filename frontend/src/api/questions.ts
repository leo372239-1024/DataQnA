/** 问数 API：提交问题 + SSE 流式消费（fetch + ReadableStream，EventSource 无法带自定义头）。 */
import { API_BASE } from "./client";
import { AgentEventSchema, QuestionOutSchema } from "./schemas";
import type { AgentEvent, QuestionCreate, QuestionOut } from "./schemas";
import { post } from "./client";

export function submitQuestion(body: QuestionCreate): Promise<QuestionOut> {
  return post("/questions", body, QuestionOutSchema);
}

/** SSE 事件流生成器：逐事件解析、Zod 校验后 yield。 */
export async function* streamQuestion(
  questionId: string,
  signal?: AbortSignal,
): AsyncGenerator<AgentEvent> {
  const res = await fetch(`${API_BASE}/questions/${questionId}/stream`, {
    headers: { Accept: "text/event-stream" },
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`SSE 流打开失败：${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let eventName = "";

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE 帧以空行分隔
      let idx: number;
      while ((idx = buffer.indexOf("\n\n")) >= 0) {
        const frame = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        let dataLine = "";
        for (const line of frame.split("\n")) {
          if (line.startsWith("event:")) eventName = line.slice(6).trim();
          else if (line.startsWith("data:")) dataLine = line.slice(5).trim();
        }
        if (!dataLine) continue;
        let raw: unknown;
        try {
          raw = JSON.parse(dataLine);
        } catch {
          continue;
        }
        // 后端 SSE 事件名（status/subgoal/answer/...）已映射为 type；直接用 payload 的 type 标签
        const parsed = AgentEventSchema.safeParse(raw);
        if (parsed.success) yield parsed.data;
        // 忽略无法校验的帧（如后端新增事件名但 payload 是 status），记录不了日志则静默跳过
        void eventName;
      }
    }
  } finally {
    reader.releaseLock();
  }
}
