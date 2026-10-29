/** 技能与工具页：展示路由可用的统一资产（skill/tool）及权限/风险。 */
import { Alert, Card, Spin, Table, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useQuery } from "@tanstack/react-query";
import { listAssets } from "../../api/assets";
import type { AssetOut } from "../../api/schemas";

const RISK_COLOR: Record<string, string> = { low: "green", medium: "orange", high: "red" };

export function AssetsPage() {
  const assets = useQuery({ queryKey: ["assets"], queryFn: () => listAssets() });

  const columns: ColumnsType<AssetOut> = [
    { title: "ID", dataIndex: "id", key: "id", width: 180 },
    {
      title: "类型",
      dataIndex: "kind",
      key: "kind",
      width: 80,
      render: (k: string) => <Tag color={k === "skill" ? "blue" : "gold"}>{k}</Tag>,
    },
    { title: "名称", dataIndex: "name", key: "name", width: 140 },
    { title: "能力", dataIndex: "capability", key: "capability", ellipsis: true },
    { title: "别名", dataIndex: "aliases", key: "aliases", render: (a: string[]) => a.slice(0, 5).map((x) => <Tag key={x}>{x}</Tag>) },
    {
      title: "权限",
      dataIndex: "permissions",
      key: "permissions",
      width: 120,
      render: (p: string[]) => (p.length ? p.map((x) => <Tag key={x} color="red">{x}</Tag>) : <Tag>公开</Tag>),
    },
    {
      title: "风险",
      dataIndex: "risk",
      key: "risk",
      width: 80,
      render: (r: string) => <Tag color={RISK_COLOR[r] ?? "default"}>{r}</Tag>,
    },
    {
      title: "需确认",
      dataIndex: "requires_confirmation",
      key: "requires_confirmation",
      width: 80,
      render: (v: boolean) => (v ? <Tag color="orange">HITL</Tag> : "—"),
    },
  ];

  if (assets.isLoading) return <Spin />;
  if (assets.isError) return <Alert type="error" message="资产加载失败" />;

  return (
    <Card title="技能与工具（统一资产路由）">
      <Table
        rowKey="id"
        size="small"
        columns={columns}
        dataSource={assets.data ?? []}
        pagination={false}
        scroll={{ x: 900 }}
      />
    </Card>
  );
}
