/** Trace 时间线：把 span 列表渲染为可读的执行链（树形 + 时长）。 */
import { useMemo } from "react";
import { Table, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { SpanOut } from "../api/schemas";
import { formatBytes, formatDuration } from "../lib/format";

const KIND_COLOR: Record<string, string> = {
  intent: "geekblue",
  plan: "geekblue",
  route: "purple",
  dsl: "cyan",
  sql_exec: "blue",
  tool: "gold",
  llm: "magenta",
  guard: "red",
  reflection: "green",
};

const STATUS_COLOR: Record<string, string> = {
  ok: "green",
  error: "red",
  blocked: "orange",
};

interface TraceTimelineProps {
  spans: SpanOut[];
  className?: string;
}

export function TraceTimeline({ spans, className }: TraceTimelineProps) {
  const rows = useMemo(() => {
    const sorted = [...spans].sort((a, b) => a.span_id.localeCompare(b.span_id));
    // 计算树形缩进层级
    const depth = new Map<string, number>();
    const byId = new Map(sorted.map((s) => [s.span_id, s]));
    const calc = (s: SpanOut): number => {
      if (depth.has(s.span_id)) return depth.get(s.span_id)!;
      const d = s.parent_span_id && byId.has(s.parent_span_id) ? calc(byId.get(s.parent_span_id)!) + 1 : 0;
      depth.set(s.span_id, d);
      return d;
    };
    sorted.forEach(calc);
    return sorted.map((s) => ({ ...s, depth: depth.get(s.span_id) ?? 0 }));
  }, [spans]);

  const columns: ColumnsType<(typeof rows)[number]> = [
    {
      title: "Span",
      dataIndex: "name",
      key: "name",
      render: (name: string, r) => (
        <span style={{ paddingLeft: r.depth * 16 }}>
          <Tag color={KIND_COLOR[r.kind] ?? "default"}>{r.kind}</Tag>
          {name}
        </span>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 90,
      render: (s: string, r) => (
        <Tag color={STATUS_COLOR[s] ?? "default"}>{r.failure_code ? r.failure_code : s}</Tag>
      ),
    },
    {
      title: "耗时",
      dataIndex: "duration_ms",
      key: "duration_ms",
      width: 110,
      render: (v: number) => formatDuration(v),
    },
    {
      title: "扫描",
      dataIndex: "scanned_bytes",
      key: "scanned_bytes",
      width: 100,
      render: (v: number) => (v > 0 ? formatBytes(v) : "—"),
    },
    {
      title: "token",
      key: "tokens",
      width: 90,
      render: (_, r) => (r.token_in + r.token_out > 0 ? `${r.token_in}→${r.token_out}` : "—"),
    },
    {
      title: "模型/资产",
      key: "meta",
      width: 140,
      render: (_, r) => r.model || r.asset_id || "—",
    },
  ];

  return (
    <Table
      className={className}
      rowKey="span_id"
      size="small"
      columns={columns}
      dataSource={rows}
      pagination={false}
      scroll={{ x: 720 }}
    />
  );
}
