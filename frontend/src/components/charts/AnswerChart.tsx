/** 答案图表渲染：把后端 chart 配置映射为 ECharts option（涨红跌绿）。 */
import { useMemo } from "react";
import { EChart } from "./EChart";
import type { ECOption } from "./EChart";
import { chartTheme } from "../../lib/chartTheme";
import { parseMoney } from "../../lib/format";
import { useSessionStore } from "../../stores/session";

interface AnswerChartProps {
  chart: Record<string, unknown> | null | undefined;
  className?: string;
}

export function AnswerChart({ chart, className }: AnswerChartProps) {
  const dark = useSessionStore((s) => s.dark);
  const t = chartTheme(dark);

  const option = useMemo<ECOption | null>(() => {
    if (!chart) return null;
    const type = chart.type;
    if (type === "waterfall") {
      const items = (chart.items as Array<Record<string, unknown>>) ?? [];
      const cats = items.map((it) => String(it.dimension_value ?? ""));
      const vals = items.map((it) => parseMoney(it.contribution));
      return {
        textStyle: { color: t.text },
        tooltip: { trigger: "axis" },
        grid: { left: 48, right: 24, top: 32, bottom: 48 },
        xAxis: { type: "category", data: cats, axisLabel: { color: t.axis, rotate: 30 } },
        yAxis: { type: "value", axisLabel: { color: t.axis } },
        series: [
          {
            type: "bar",
            data: vals.map((v) => ({ value: v, itemStyle: { color: v >= 0 ? t.up : t.down } })),
            label: { show: true, position: "top", color: t.text },
          },
        ],
      };
    }
    if (type === "bar") {
      const items = (chart.items as Array<Record<string, unknown>>) ?? [];
      const dim = String(chart.dimension ?? "dim");
      const cats = items.map((it) => String(it[dim] ?? ""));
      const vals = items.map((it) => parseMoney(it.m0 ?? it.value));
      return {
        textStyle: { color: t.text },
        tooltip: { trigger: "axis" },
        grid: { left: 56, right: 24, top: 32, bottom: 48 },
        xAxis: { type: "category", data: cats, axisLabel: { color: t.axis, rotate: 30 } },
        yAxis: { type: "value", axisLabel: { color: t.axis } },
        series: [{ type: "bar", data: vals, itemStyle: { color: t.primary } }],
      };
    }
    if (type === "compare") {
      const cur = parseMoney(chart.current);
      const base = parseMoney(chart.baseline);
      const delta = parseMoney(chart.delta);
      return {
        textStyle: { color: t.text },
        tooltip: { trigger: "axis" },
        grid: { left: 56, right: 24, top: 32, bottom: 40 },
        xAxis: { type: "category", data: ["对比期", "当前期"], axisLabel: { color: t.axis } },
        yAxis: { type: "value", axisLabel: { color: t.axis } },
        series: [
          {
            type: "bar",
            data: [
              { value: base, itemStyle: { color: t.axis } },
              { value: cur, itemStyle: { color: delta >= 0 ? t.up : t.down } },
            ],
          },
        ],
      };
    }
    if (type === "report") {
      const items = (chart.items as Array<Record<string, unknown>>) ?? [];
      const cats = items.map((it) => String(it.name_cn ?? it.metric_id ?? ""));
      const vals = items.map((it) => parseMoney(it.value));
      return {
        textStyle: { color: t.text },
        tooltip: { trigger: "axis" },
        grid: { left: 56, right: 24, top: 32, bottom: 48 },
        xAxis: { type: "category", data: cats, axisLabel: { color: t.axis, rotate: 30 } },
        yAxis: { type: "value", axisLabel: { color: t.axis } },
        series: [{ type: "bar", data: vals, itemStyle: { color: t.primary } }],
      };
    }
    return null;
  }, [chart, t]);

  if (!option) return null;
  return <EChart className={className} option={option} ariaLabel="分析结果图表" />;
}
