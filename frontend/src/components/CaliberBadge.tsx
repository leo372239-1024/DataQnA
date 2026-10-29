/** 口径徽标：展示指标口径（来自注册表，非 LLM 生成）。 */
import { Tag, Tooltip } from "antd";

interface CaliberBadgeProps {
  caliber: string;
  className?: string;
}

export function CaliberBadge({ caliber, className }: CaliberBadgeProps) {
  if (!caliber) return null;
  return (
    <Tooltip title={`口径：${caliber}`}>
      <Tag color="blue" className={className} style={{ maxWidth: 360, overflow: "hidden", textOverflow: "ellipsis" }}>
        口径 · {caliber}
      </Tag>
    </Tooltip>
  );
}
