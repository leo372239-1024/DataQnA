/** 评测看板页：触发评测跑分 + 展示 summary。 */
import { useState } from "react";
import { Alert, Button, Card, Descriptions, Select, Space, Tag, Typography } from "antd";
import { useMutation } from "@tanstack/react-query";
import { runEval } from "../../api/evals";
import type { EvalRunRequest, EvalRunOut } from "../../api/schemas";

const { Text } = Typography;

const SUITES = [
  { value: "gold", label: "黄金集（EX）" },
  { value: "routing", label: "路由（A/B）" },
  { value: "redteam", label: "红队（安全）" },
  { value: "reflection", label: "反思（A/B）" },
  { value: "longtask", label: "长时程（A/B）" },
];

export function EvalsPage() {
  const [suite, setSuite] = useState("gold");
  const [baseline, setBaseline] = useState<"on" | "off">("off");

  const run = useMutation({
    mutationFn: () => {
      const body: EvalRunRequest = { suite, level: "L1-L5", baseline };
      return runEval(body);
    },
  });

  return (
    <Card title="评测看板">
      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          value={suite}
          onChange={setSuite}
          options={SUITES}
          style={{ width: 200 }}
        />
        {["routing", "reflection", "longtask"].includes(suite) && (
          <Select
            value={baseline}
            onChange={setBaseline}
            options={[
              { value: "off", label: "改进后（off）" },
              { value: "on", label: "基线（on）" },
            ]}
            style={{ width: 160 }}
          />
        )}
        <Button type="primary" loading={run.isPending} onClick={() => run.mutate()}>
          运行评测
        </Button>
      </Space>

      {run.isSuccess && run.data ? (
        <EvalSummary result={run.data} />
      ) : run.isError ? (
        <Alert type="error" message="评测运行失败" />
      ) : (
        <Text type="secondary">选择套件并运行，结果将在此展示。</Text>
      )}
    </Card>
  );
}

function EvalSummary({ result }: { result: EvalRunOut }) {
  const s = result.summary as Record<string, unknown>;
  const entries = Object.entries(s)
    .filter(([k]) => !["suite", "cases", "total", "failure_breakdown", "per_level", "baseline"].includes(k))
    .map(([k, v]) => ({ key: k, value: v }));

  const rate = (v: unknown) =>
    typeof v === "number" ? `${(v * 100).toFixed(1)}%` : String(v);

  return (
    <>
      <Alert
        type={result.status === "done" ? "success" : "warning"}
        showIcon
        message={`套件 ${result.suite} 运行${result.status === "done" ? "完成" : result.status}`}
        style={{ marginBottom: 16 }}
      />
      <Descriptions column={2} bordered size="small">
        {entries.map((e) => (
          <Descriptions.Item key={e.key} label={e.key}>
            {e.key.includes("rate") || e.key.includes("accuracy") || e.key === "EX" || e.key.includes("consistency") || e.key.includes("traceability") ? (
              <Tag color="blue">{rate(e.value)}</Tag>
            ) : (
              String(e.value)
            )}
          </Descriptions.Item>
        ))}
      </Descriptions>
    </>
  );
}
