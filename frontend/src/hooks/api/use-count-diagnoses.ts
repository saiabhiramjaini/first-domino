"use client";

import { useQuery } from "@tanstack/react-query";

import { countDiagnoses, type CountDiagnosesRequest } from "@/api/generated";
import { zCountDiagnosesResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { useApiAuth } from "./use-api-auth";

export const countDiagnosesKey = (filters: CountDiagnosesRequest) =>
  ["diagnoses", "count", filters] as const;

export function useCountDiagnoses(filters: CountDiagnosesRequest) {
  const { auth, isReady } = useApiAuth();
  return useQuery({
    queryKey: countDiagnosesKey(filters),
    queryFn: () => callApi(countDiagnoses({ auth, body: filters }), zCountDiagnosesResponse),
    enabled: isReady,
    select: (data) => data.count,
  });
}
