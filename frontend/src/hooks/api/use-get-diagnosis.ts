"use client";

import { useQuery } from "@tanstack/react-query";

import { getDiagnosis } from "@/api/generated";
import { zGetDiagnosisResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { LIVE_REFRESH_MS, isDiagnosisActive } from "./diagnosis-activity";
import { useApiAuth } from "./use-api-auth";

export const getDiagnosisKey = (diagnosisId: string) => ["diagnoses", "get", diagnosisId] as const;

export function useGetDiagnosis(diagnosisId: string | null) {
  const { auth, isReady } = useApiAuth();
  return useQuery({
    queryKey: getDiagnosisKey(diagnosisId ?? ""),
    queryFn: () =>
      callApi(
        getDiagnosis({ auth, query: { diagnosis_id: diagnosisId ?? "" } }),
        zGetDiagnosisResponse
      ),
    enabled: isReady && diagnosisId !== null,
    select: (data) => data.diagnosis,
    refetchInterval: (query) =>
      isDiagnosisActive(query.state.data?.diagnosis.status) ? LIVE_REFRESH_MS : false,
  });
}
