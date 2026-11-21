"use client";

import { useQuery } from "@tanstack/react-query";

import { countCauses, type CountCausesRequest } from "@/api/generated";
import { zCountCausesResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { useApiAuth } from "./use-api-auth";

export const countCausesKey = (filters: CountCausesRequest) =>
  ["causes", "count", filters] as const;

type CountOptions = { refreshMs?: number | false };

export function useCountCauses(
  filters: CountCausesRequest,
  { refreshMs = false }: CountOptions = {}
) {
  const { auth, isReady } = useApiAuth();
  return useQuery({
    queryKey: countCausesKey(filters),
    queryFn: () => callApi(countCauses({ auth, body: filters }), zCountCausesResponse),
    enabled: isReady,
    select: (data) => data.count,
    refetchInterval: refreshMs,
  });
}
