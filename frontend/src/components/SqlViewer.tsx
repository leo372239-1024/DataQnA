/** SQL 查看器：展示后端生成的参数化只读 SQL，可复制。 */
import { useState } from "react";
import { Button, Space, Typography } from "antd";
import { CopyOutlined, CheckOutlined } from "@ant-design/icons";

interface SqlViewerProps {
  sql: string;
  className?: string;
}

export function SqlViewer({ sql, className }: SqlViewerProps) {
  const [copied, setCopied] = useState(false);
  if (!sql) return null;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* 剪贴板不可用时静默忽略 */
    }
  };

  return (
    <div className={className}>
      <Space style={{ marginBottom: 8, justifyContent: "space-between", width: "100%" }}>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          参数化只读 SQL（RLS 已注入）
        </Typography.Text>
        <Button size="small" icon={copied ? <CheckOutlined /> : <CopyOutlined />} onClick={copy}>
          {copied ? "已复制" : "复制"}
        </Button>
      </Space>
      <pre
        style={{
          background: "var(--dq-code-bg, #f6f8fa)",
          border: "1px solid #e8e8e8",
          borderRadius: 6,
          padding: 12,
          overflow: "auto",
          fontSize: 12,
          lineHeight: 1.6,
          margin: 0,
          fontFamily: "SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace",
        }}
      >
        {sql}
      </pre>
    </div>
  );
}
