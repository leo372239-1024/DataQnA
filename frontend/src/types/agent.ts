/** Agent 领域类型 —— 与后端 SSE/agent 契约 1:1。Zod 已定义于 api/schemas.ts，此处仅做语义导出与派生类型。 */
import type { AgentEvent, AnswerOut } from "../api/schemas";

export type { AgentEvent, AnswerOut };

export type SubgoalTraceItem = {
  id: string;
  status: string;
  failure_code?: string;
};
