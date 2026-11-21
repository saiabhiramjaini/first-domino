"use client";

import { useQuery } from "@tanstack/react-query";

import { listChecks } from "@/api/generated";
import { zListChecksResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { LIVE_REFRESH_MS } from "./diagnosis-activity";
import { useApiAuth } from "./use-api-auth";

const MAX_CHECKS = 100;

export const listChecksKey = (diagnosisId: string) => ["checks", "list", diagnosisId] as const;

type UseListChecksOptions = { isLive: boolean };

export function useListChecks(diagnosisId: string | null, { isLive }: UseListChecksOptions) {
  const { auth, isReady } = useApiAuth();
  return useQuery({
    queryKey: listChecksKey(diagnosisId ?? ""),
    queryFn: () =>
      callApi(
        listChecks({ auth, body: { diagnosis_id: diagnosisId ?? "", limit: MAX_CHECKS } }),
        zListChecksResponse
      ),
    enabled: isReady && diagnosisId !== null,
    select: (data) => data.items,
    refetchInterval: isLive ? LIVE_REFRESH_MS : false,
  });
}
