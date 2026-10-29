/** 语义层管理页：指标/维度注册表只读浏览 + 指标详情（口径/血缘）。 */
import { useState } from "react";
import { Alert, Card, Descriptions, Drawer, Empty, Spin, Table, Tabs, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useQuery } from "@tanstack/react-query";
import { getMetric, listDimensions, listMetrics } from "../../api/semantic";
import type { DimensionOut, MetricOut } from "../../api/schemas";

const { Text } = Typography;

export function SemanticPage() {
  const [selected, setSelected] = useState<string | null>(null);

  const metrics = useQuery({ queryKey: ["metrics"], queryFn: () => listMetrics() });
  const dimensions = useQuery({ queryKey: ["dimensions"], queryFn: () => listDimensions() });
  const detail = useQuery({
    queryKey: ["metric", selected],
    queryFn: () => getMetric(selected!),
    enabled: Boolean(selected),
  });

  const metricColumns: ColumnsType<MetricOut> = [
    { title: "ID", dataIndex: "id", key: "id", width: 180 },
    { title: "名称", dataIndex: "name_cn", key: "name_cn", width: 140 },
    {
      title: "别名",
      dataIndex: "aliases",
      key: "aliases",
      render: (a: string[]) => a.slice(0, 4).map((x) => <Tag key={x}>{x}</Tag>),
    },
    {
      title: "类型",
      dataIndex: "type",
      key: "type",
      width: 100,
      render: (t: string) => <Tag color={t === "ratio" ? "purple" : "blue"}>{t}</Tag>,
    },
    { title: "口径", dataIndex: "caliber_cn", key: "caliber_cn", ellipsis: true },
    { title: "版本", dataIndex: "version", key: "version", width: 70, render: (v: number) => `v${v}` },
  ];

  const dimColumns: ColumnsType<DimensionOut> = [
    { title: "ID", dataIndex: "id", key: "id", width: 160 },
    { title: "名称", dataIndex: "name_cn", key: "name_cn", width: 140 },
    { title: "别名", dataIndex: "aliases", key: "aliases", render: (a: string[]) => a.slice(0, 6).map((x) => <Tag key={x}>{x}</Tag>) },
    { title: "层级", dataIndex: "hierarchy", key: "hierarchy", render: (h: string[]) => h.join(" → ") },
    { title: "基数估计", dataIndex: "cardinality_estimate", key: "cardinality_estimate", width: 100 },
  ];

  return (
    <Card title="语义层管理">
      <Tabs
        items={[
          {
            key: "metrics",
            label: `指标（${metrics.data?.total ?? 0}）`,
            children: metrics.isLoading ? (
              <Spin />
            ) : metrics.isError ? (
              <Alert type="error" message="指标加载失败" />
            ) : (
              <Table
                rowKey="id"
                size="small"
                columns={metricColumns}
                dataSource={metrics.data?.items ?? []}
                pagination={{ pageSize: 12 }}
                onRow={(r) => ({ onClick: () => setSelected(r.id), style: { cursor: "pointer" } })}
              />
            ),
          },
          {
            key: "dimensions",
            label: `维度（${dimensions.data?.total ?? 0}）`,
            children: dimensions.isLoading ? (
              <Spin />
            ) : (
              <Table
                rowKey="id"
                size="small"
                columns={dimColumns}
                dataSource={dimensions.data?.items ?? []}
                pagination={{ pageSize: 12 }}
              />
            ),
          },
        ]}
      />

      <Drawer
        title={detail.data ? `指标口径 · ${detail.data.name_cn}` : "指标口径"}
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        width={520}
      >
        {detail.isLoading ? (
          <Spin />
        ) : detail.data ? (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="ID">{detail.data.id}</Descriptions.Item>
            <Descriptions.Item label="口径">{detail.data.caliber_cn || "—"}</Descriptions.Item>
            <Descriptions.Item label="类型">{detail.data.type}</Descriptions.Item>
            <Descriptions.Item label="表达式">{detail.data.expression ?? "—"}</Descriptions.Item>
            <Descriptions.Item label="分子">{detail.data.numerator ?? "—"}</Descriptions.Item>
            <Descriptions.Item label="分母">{detail.data.denominator ?? "—"}</Descriptions.Item>
            <Descriptions.Item label="源表">
              {detail.data.source_tables.map((t) => (
                <Tag key={t}>{t}</Tag>
              ))}
            </Descriptions.Item>
            <Descriptions.Item label="血缘">
              {detail.data.lineage.length ? (
                detail.data.lineage.map((n) => (
                  <Tag key={n.metric_id} color="cyan">
                    {n.name_cn} v{n.version}
                  </Tag>
                ))
              ) : (
                <Text type="secondary">原子指标，无上游血缘</Text>
              )}
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Empty description="未选择指标" />
        )}
      </Drawer>
    </Card>
  );
}
