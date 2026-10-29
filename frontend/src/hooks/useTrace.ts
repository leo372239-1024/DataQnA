import { useQuery } from "@tanstack/react-query";
import { getTrace } from "../api/traces";

export function useTrace(traceId: string | null | undefined) {
  return useQuery({
    queryKey: ["trace", traceId],
    queryFn: () => getTrace(traceId!),
    enabled: Boolean(traceId),
    staleTime: 10_000,
  });
}
