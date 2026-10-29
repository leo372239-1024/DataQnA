import { describe, expect, it } from "vitest";
import { formatCNY, formatPercent, parseMoney, formatSigned, formatBytes } from "./format";

describe("format", () => {
  it("parseMoney 解析字符串数字", () => {
    expect(parseMoney("1234.5")).toBe(1234.5);
    expect(parseMoney("1,234.5")).toBe(1234.5);
    expect(parseMoney(null)).toBe(0);
  });

  it("formatCNY 千分位 + 人民币符号", () => {
    expect(formatCNY("1234567.8")).toBe("¥1,234,567.8");
  });

  it("formatPercent 百分比", () => {
    expect(formatPercent(0.1234)).toBe("12.34%");
  });

  it("formatSigned 带符号差值", () => {
    expect(formatSigned(12.3)).toBe("+12.3");
    expect(formatSigned(-12.3)).toBe("−12.3");
  });

  it("formatBytes 人类可读", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(51200)).toBe("50 KB");
  });
});
