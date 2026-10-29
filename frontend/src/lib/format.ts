/** 数字/金额/百分比的统一格式化。UI 层只允许通过这里的函数格式化。 */

const _cnNumber = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 });
const _cnNumber0 = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 });

/** 解析后端 NUMERIC 字符串/数字 → number。 */
export function parseMoney(value: unknown): number {
  if (value === null || value === undefined || value === "") return 0;
  if (typeof value === "number") return value;
  const n = Number(String(value).replace(/,/g, ""));
  return Number.isFinite(n) ? n : 0;
}

/** 人民币格式化：¥1,234.56。 */
export function formatCNY(value: unknown): string {
  return `¥${_cnNumber.format(parseMoney(value))}`;
}

/** 普通数字（千分位，最多 2 位小数）。 */
export function formatNumber(value: unknown): string {
  return _cnNumber.format(parseMoney(value));
}

/** 整数（千分位，无小数）。 */
export function formatInteger(value: unknown): string {
  return _cnNumber0.format(parseMoney(value));
}

/** 百分比：输入 0.1234 → "12.34%"。 */
export function formatPercent(value: unknown): string {
  const n = parseMoney(value);
  return `${(n * 100).toFixed(2)}%`;
}

/** 带符号的差值：+12.34 或 −12.34。 */
export function formatSigned(value: unknown): string {
  const n = parseMoney(value);
  const sign = n > 0 ? "+" : n < 0 ? "−" : "";
  return `${sign}${_cnNumber.format(Math.abs(n))}`;
}

/** 字节数 → 人类可读。 */
export function formatBytes(bytes: number): string {
  if (bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let v = bytes;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  const rounded = v >= 100 || i === 0 ? Math.round(v) : Math.round(v * 10) / 10;
  return `${rounded} ${units[i]}`;
}

/** 毫秒 → 人类可读时长。 */
export function formatDuration(ms: number): string {
  if (ms < 1) return "<1 ms";
  if (ms < 1000) return `${ms.toFixed(0)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}
