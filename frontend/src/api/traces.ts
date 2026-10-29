import { get } from "./client";
import { TraceOutSchema } from "./schemas";
import type { TraceOut } from "./schemas";

export function getTrace(traceId: string): Promise<TraceOut> {
  return get(`/traces/${traceId}`, TraceOutSchema);
}
