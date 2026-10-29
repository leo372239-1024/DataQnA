/** ECharts 薄封装：init/setOption/resize/dispose + 文本回退。按需注册，避免全量打包。 */
import { useEffect, useRef } from "react";
import * as echarts from "echarts/core";
import { BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { ComposeOption } from "echarts/core";
import type { BarSeriesOption } from "echarts/charts";
import type { GridComponentOption, TooltipComponentOption } from "echarts/components";

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer]);

/** 按需组合后的 option 类型（bar + grid/tooltip），保证类型安全的同时不打包无关组件。 */
export type ECOption = ComposeOption<BarSeriesOption | GridComponentOption | TooltipComponentOption>;

interface EChartProps {
  option: ECOption;
  height?: number;
  ariaLabel?: string;
  className?: string;
}

export function EChart({ option, height = 320, ariaLabel, className }: EChartProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chartRef.current = chart;
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, true);
  }, [option]);

  return (
    <div
      ref={ref}
      className={className}
      style={{ width: "100%", height }}
      role="img"
      aria-label={ariaLabel ?? "数据图表"}
    />
  );
}
