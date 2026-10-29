/** 执行追踪页：输入 trace_id 查看 span 时间线。 */
import { useState } from "react";
import { Alert, Card, Empty, Input, Space, Spin, Typography } from "antd";
import { useTrace } from "../../hooks/useTrace";
import { TraceTimeline } from "../../components/TraceTimeline";

const { Text } = Typography;

export function TracesPage() {
  const [traceId, setTraceId] = useState("");
  const [submitted, setSubmitted] = useState<string | null>(null);
  const trace = useTrace(submitted);

  return (
    <Card title="执行追踪（Trace）">
      <Space.Compact style={{ width: 420, marginBottom: 16 }}>
        <Input
          value={traceId}
          onChange={(e) => setTraceId(e.target.value)}
          placeholder="输入 trace_id（从问数结果中获取）"
          onPressEnter={() => setSubmitted(traceId.trim() || null)}
        />
        <Input.Search
          aria-label="查询 trace"
          style={{ width: 48 }}
          onSearch={() => setSubmitted(traceId.trim() || null)}
        />
      </Space.Compact>

      {!submitted ? (
        <Empty description="输入 trace_id 查看本次问数的完整执行链路" />
      ) : trace.isLoading ? (
        <Spin />
      ) : trace.isError ? (
        <Alert type="error" message="trace 不存在或加载失败" />
      ) : (
        <>
          <Text type="secondary">trace_id：{trace.data?.trace_id}</Text>
          <TraceTimeline spans={trace.data?.spans ?? []} />
        </>
      )}
    </Card>
  );
}
