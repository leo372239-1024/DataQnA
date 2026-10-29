/** Zod schema —— 前后端线缆契约的唯一真相源。类型从 schema 推断，禁止手写 interface 重复。 */
import { z } from "zod";

// ---- 通用 ----

export const ErrorBodySchema = z.object({
  code: z.string(),
  detail: z.string().optional(),
  failure_code: z.string().nullable().optional(),
  trace_id: z.string().optional(),
});

export const PageMetaSchema = z.object({
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
});

// ---- 问数 ----

export const QuestionCreateSchema = z.object({
  question: z.string().min(1).max(2000),
  tenant_id: z.string().default("t1"),
  user_id: z.string().default("demo"),
  roles: z.array(z.string()).default(["analyst"]),
  timezone: z.string().default("Asia/Shanghai"),
});
// 请求体：带默认值的字段可选（input 类型），服务端填默认
export type QuestionCreate = z.input<typeof QuestionCreateSchema>;

export const QuestionOutSchema = z.object({
  question_id: z.string(),
  question: z.string(),
  tenant_id: z.string(),
  status: z.string(),
  trace_id: z.string().nullable().optional(),
});
export type QuestionOut = z.infer<typeof QuestionOutSchema>;

// ---- SSE 事件（discriminated union，type 为 tag） ----

export const LineageNodeSchema = z.object({
  metric_id: z.string(),
  name_cn: z.string(),
  version: z.number(),
});
export type LineageNode = z.infer<typeof LineageNodeSchema>;

export const SubgoalStartSchema = z.object({
  type: z.literal("subgoal"),
  subgoal_id: z.string(),
  name: z.string().optional(),
  kind: z.string().optional(),
  status: z.string().optional(),
});

// status 事件中的计划子目标（含 DAG 依赖），运行态状态由前端 reducer 追踪
export const SubgoalPlanSchema = z.object({
  id: z.string(),
  name: z.string(),
  kind: z.string(),
  deps: z.array(z.string()),
});
export type SubgoalPlan = z.infer<typeof SubgoalPlanSchema>;

export const StatusEventSchema = z.object({
  type: z.literal("status"),
  level: z.string().optional(),
  metrics: z.array(z.string()).optional(),
  dimensions: z.array(z.string()).optional(),
  subgoals: z.array(SubgoalPlanSchema).optional(),
  evidence: z.record(z.unknown()).optional(),
});

export const AnswerEventSchema = z.object({
  type: z.literal("answer"),
  level: z.string(),
  value: z.union([z.number(), z.string()]).nullable(),
  rows: z.array(z.record(z.unknown())).default([]),
  caliber: z.string().default(""),
  sql: z.string().default(""),
  lineage: z.array(LineageNodeSchema).default([]),
  chart: z.record(z.unknown()).nullable().optional(),
  conclusion: z.string().default(""),
});

export const ClarificationEventSchema = z.object({
  type: z.literal("clarification"),
  reason: z.string().optional(),
  detail: z.string().optional(),
});

export const BlockedEventSchema = z.object({
  type: z.literal("blocked"),
  code: z.string().optional(),
  detail: z.string().optional(),
});

export const ErrorEventSchema = z.object({
  type: z.literal("error"),
  error: z.object({
    code: z.string(),
    detail: z.string().optional(),
    trace_id: z.string().optional(),
  }),
});

export const DoneEventSchema = z.object({
  type: z.literal("done"),
  trace_id: z.string().optional(),
  question_id: z.string().optional(),
});

export const AgentEventSchema = z.discriminatedUnion("type", [
  StatusEventSchema,
  SubgoalStartSchema,
  AnswerEventSchema,
  ClarificationEventSchema,
  BlockedEventSchema,
  ErrorEventSchema,
  DoneEventSchema,
]);
export type AgentEvent = z.infer<typeof AgentEventSchema>;

// ---- 答案 ----

export const AnswerOutSchema = z.object({
  question_id: z.string(),
  level: z.string().nullable(),
  value: z.union([z.number(), z.string()]).nullable(),
  rows: z.array(z.record(z.unknown())).default([]),
  caliber: z.string().default(""),
  sql: z.string().default(""),
  lineage: z.array(LineageNodeSchema).default([]),
  chart: z.record(z.unknown()).nullable(),
  conclusion: z.string().default(""),
  subgoal_trace: z.array(z.record(z.unknown())).default([]),
  trace_id: z.string().nullable(),
});
export type AnswerOut = z.infer<typeof AnswerOutSchema>;

// ---- 语义层 ----

export const MetricOutSchema = z.object({
  id: z.string(),
  name_cn: z.string(),
  aliases: z.array(z.string()),
  type: z.string(),
  unit: z.string().default(""),
  caliber_cn: z.string().default(""),
  owner: z.string().default(""),
  version: z.number(),
  tags: z.array(z.string()),
  risk_level: z.string(),
});
export type MetricOut = z.infer<typeof MetricOutSchema>;

export const MetricListSchema = PageMetaSchema.extend({ items: z.array(MetricOutSchema) });

export const MetricDetailSchema = MetricOutSchema.extend({
  expression: z.string().nullable(),
  numerator: z.string().nullable(),
  denominator: z.string().nullable(),
  source_tables: z.array(z.string()),
  default_time_col: z.string().nullable(),
  lineage: z.array(LineageNodeSchema),
});
export type MetricDetail = z.infer<typeof MetricDetailSchema>;

export const DimensionOutSchema = z.object({
  id: z.string(),
  name_cn: z.string(),
  aliases: z.array(z.string()),
  hierarchy: z.array(z.string()),
  cardinality_estimate: z.number(),
});
export type DimensionOut = z.infer<typeof DimensionOutSchema>;

export const DimensionListSchema = PageMetaSchema.extend({ items: z.array(DimensionOutSchema) });

// ---- 资产 ----

export const AssetOutSchema = z.object({
  id: z.string(),
  kind: z.string(),
  name: z.string(),
  description: z.string(),
  aliases: z.array(z.string()),
  domains: z.array(z.string()),
  capability: z.string(),
  permissions: z.array(z.string()),
  risk: z.string(),
  deprecated: z.boolean(),
  requires_confirmation: z.boolean(),
});
export type AssetOut = z.infer<typeof AssetOutSchema>;

// ---- trace ----

export const SpanOutSchema = z.object({
  trace_id: z.string(),
  span_id: z.string(),
  parent_span_id: z.string().nullable(),
  kind: z.string(),
  name: z.string(),
  status: z.string(),
  duration_ms: z.number(),
  token_in: z.number(),
  token_out: z.number(),
  model: z.string(),
  scanned_bytes: z.number(),
  failure_code: z.string().nullable(),
  asset_id: z.string().nullable(),
  semantic_version: z.number().nullable(),
});
export type SpanOut = z.infer<typeof SpanOutSchema>;

export const TraceOutSchema = z.object({
  trace_id: z.string(),
  spans: z.array(SpanOutSchema),
});
export type TraceOut = z.infer<typeof TraceOutSchema>;

// ---- 评测 ----

export const EvalRunRequestSchema = z.object({
  suite: z.string().default("gold"),
  level: z.string().default("L1-L5"),
  baseline: z.enum(["on", "off"]).default("on"),
});
export type EvalRunRequest = z.infer<typeof EvalRunRequestSchema>;

export const EvalRunOutSchema = z.object({
  run_id: z.string(),
  suite: z.string(),
  status: z.string(),
  summary: z.record(z.unknown()).default({}),
});
export type EvalRunOut = z.infer<typeof EvalRunOutSchema>;

// ---- meta ----

export const MetaSchema = z.object({
  app: z.string(),
  semantic_version: z.number(),
  metric_count: z.number(),
  dimension_count: z.number(),
  asset_count: z.number(),
  snapshot_date: z.string(),
  llm_provider: z.string(),
});
export type Meta = z.infer<typeof MetaSchema>;
