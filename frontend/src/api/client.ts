/** API 客户端核心：fetch 封装 + 认证头 + 错误映射 + Zod 边界校验。 */
import type { ZodType, ZodTypeDef } from "zod";

export const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

export class ApiError extends Error {
  constructor(
    public code: string,
    public detail: string,
    public traceId?: string,
  ) {
    super(detail || code);
    this.name = "ApiError";
  }
}

/** 认证头。MVP 无 JWT，由后端 dev 默认主体派生；预留扩展点。 */
export function authHeader(): Record<string, string> {
  return {};
}

/** 通用请求：JSON 响应用 Zod 校验后返回，失败抛 ApiError。
 *  泛型绑定 Zod 的 output 类型（T），避免 .default() 把字段推断成 input 的可选类型。 */
export async function request<T>(
  path: string,
  schema: ZodType<T, ZodTypeDef, unknown>,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...authHeader() },
    ...init,
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const err = (body as { error?: { code?: string; detail?: string; trace_id?: string } } | null)
      ?.error;
    throw new ApiError(err?.code ?? "UNKNOWN", err?.detail ?? res.statusText, err?.trace_id);
  }
  const parsed = schema.safeParse(body);
  if (!parsed.success) {
    throw new ApiError("SCHEMA_MISMATCH", parsed.error.message);
  }
  return parsed.data;
}

export async function get<T>(
  path: string,
  schema: ZodType<T, ZodTypeDef, unknown>,
): Promise<T> {
  return request(path, schema);
}

export async function post<T>(
  path: string,
  body: unknown,
  schema: ZodType<T, ZodTypeDef, unknown>,
): Promise<T> {
  return request(path, schema, { method: "POST", body: JSON.stringify(body) });
}
