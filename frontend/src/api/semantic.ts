import { get } from "./client";
import {
  DimensionListSchema,
  MetricDetailSchema,
  MetricListSchema,
} from "./schemas";
import type { DimensionOut, MetricDetail, MetricOut } from "./schemas";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export async function listMetrics(type?: string): Promise<Page<MetricOut>> {
  const q = type ? `?type=${encodeURIComponent(type)}` : "";
  return get(`/semantic/metrics${q}`, MetricListSchema);
}

export async function listDimensions(): Promise<Page<DimensionOut>> {
  return get("/semantic/dimensions", DimensionListSchema);
}

export async function getMetric(metricId: string): Promise<MetricDetail> {
  return get(`/semantic/metrics/${metricId}`, MetricDetailSchema);
}
