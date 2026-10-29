/** 答案面板：展示结论、数值、图表、口径、SQL、血缘。 */
import { useMemo } from "react";
import { Alert, Col, Empty, Row, Space, Statistic, Table, Tag } from "antd";
import type { AnswerOut } from "../api/schemas";
import { CaliberBadge } from "./CaliberBadge";
import { SqlViewer } from "./SqlViewer";
import { formatCNY, formatNumber, formatPercent, parseMoney } from "../lib/format";

interface AnswerPanelProps {
  answer: AnswerOut;
  className?: string;
}

function fmtValue(v: unknown, unit: string): string {
  const n = parseMoney(v);
  if (unit === "%" || unit === "percent") return formatPercent(n);
  if (unit === "元" || unit === "金额" || unit === "CNY") return formatCNY(n);
  return formatNumber(n);
}

export function AnswerPanel({ answer, className }: AnswerPanelProps) {
  const tableData = useMemo(() => {
    if (answer.rows.length === 0) return [];
    const keys = Object.keys(answer.rows[0] ?? {});
    return answer.rows.map((r, i) => {
      const row: Record<string, unknown> = { __key: i };
      for (const k of keys) row[k] = r[k];
      return row;
    });
  }, [answer.rows]);

  if (!answer.rows.length && answer.value == null && !answer.conclusion) {
    return (
      <Empty className={className} description="本次查询未返回结果" image={Empty.PRESENTED_IMAGE_SIMPLE} />
    );
  }

  const columns = tableData.length
    ? Object.keys(answer.rows[0] ?? {}).map((k) => ({
        title: k,
        dataIndex: k,
        key: k,
        ellipsis: true,
        render: (v: unknown) => (typeof v === "number" || typeof v === "string" ? String(v) : JSON.stringify(v)),
      }))
    : [];

  return (
    <div className={className}>
      {answer.conclusion && (
        <Alert type="info" showIcon message={answer.conclusion} style={{ marginBottom: 16 }} />
      )}

      {answer.value != null && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col>
            <Statistic title="结果" value={fmtValue(answer.value, "元")} />
          </Col>
          {answer.level && (
            <Col>
              <Statistic title="分析等级" value={answer.level} />
            </Col>
          )}
        </Row>
      )}

      <Space wrap style={{ marginBottom: 12 }}>
        <CaliberBadge caliber={answer.caliber} />
        {answer.lineage.map((n) => (
          <Tag key={n.metric_id} color="cyan">
            {n.name_cn} v{n.version}
          </Tag>
        ))}
      </Space>

      {tableData.length > 0 && (
        <Table
          size="small"
          rowKey="__key"
          columns={columns}
          dataSource={tableData}
          pagination={{ pageSize: 8, hideOnSinglePage: true }}
          style={{ marginBottom: 16 }}
        />
      )}

      {answer.sql && (
        <SqlViewer sql={answer.sql} />
      )}
    </div>
  );
}
