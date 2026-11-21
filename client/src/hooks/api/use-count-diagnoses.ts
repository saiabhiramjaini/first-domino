"use client";

import { useQuery } from "@tanstack/react-query";

import { countDiagnoses, type CountDiagnosesRequest } from "@/api/generated";
import { zCountDiagnosesResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { useApiAuth } from "./use-api-auth";

export const countDiagnosesKey = (filters: CountDiagnosesRequest) =>
  ["diagnoses", "count", filters] as const;

type CountOptions = { refreshMs?: number | false };

export function useCountDiagnoses(
  filters: CountDiagnosesRequest,
  { refreshMs = false }: CountOptions = {}
) {
  const { auth, isReady } = useApiAuth();
  return useQuery({
    queryKey: countDiagnosesKey(filters),
    queryFn: () => callApi(countDiagnoses({ auth, body: filters }), zCountDiagnosesResponse),
    enabled: isReady,
    select: (data) => data.count,
    refetchInterval: refreshMs,
  });
}
