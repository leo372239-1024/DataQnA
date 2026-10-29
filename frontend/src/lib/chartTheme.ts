/** ECharts 主题单一来源：涨红跌绿（中国金融约定），明暗模式感知。 */

export interface ChartTheme {
  up: string; // 涨 / 正向 → 红
  down: string; // 跌 / 负向 → 绿
  primary: string;
  text: string;
  axis: string;
  split: string;
}

export const lightTheme: ChartTheme = {
  up: "#cf1322", // 红
  down: "#3f8600", // 绿
  primary: "#1677ff",
  text: "#1f1f1f",
  axis: "#8c8c8c",
  split: "#f0f0f0",
};

export const darkTheme: ChartTheme = {
  up: "#ff4d4f",
  down: "#52c41a",
  primary: "#4096ff",
  text: "#e6e6e6",
  axis: "#8c8c8c",
  split: "#303030",
};

/** 根据是否暗色返回图表主题。 */
export function chartTheme(dark: boolean): ChartTheme {
  return dark ? darkTheme : lightTheme;
}

/** 涨跌着色：正 → up，负 → down，零 → axis。 */
export function deltaColor(delta: number, dark: boolean): string {
  const t = chartTheme(dark);
  if (delta > 0) return t.up;
  if (delta < 0) return t.down;
  return t.axis;
}
