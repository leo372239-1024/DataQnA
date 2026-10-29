/** 语义层查询 hooks（TanStack Query，服务端状态）。 */
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { listMetrics, listDimensions } from "../api/semantic";

export const metricKeys = {
  all: ["metrics"] as const,
  list: (type?: string) => ["metrics", { type }] as const,
};

export const dimensionKeys = {
  all: ["dimensions"] as const,
};

export function useMetrics(type?: string) {
  return useQuery({
    queryKey: metricKeys.list(type),
    queryFn: () => listMetrics(type),
    staleTime: 60_000,
    placeholderData: keepPreviousData,
  });
}

export function useDimensions() {
  return useQuery({
    queryKey: dimensionKeys.all,
    queryFn: () => listDimensions(),
    staleTime: 60_000,
  });
}
