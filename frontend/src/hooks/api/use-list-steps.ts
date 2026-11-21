"use client";

import { useQuery } from "@tanstack/react-query";

import { listSteps } from "@/api/generated";
import { zListStepsResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { useApiAuth } from "./use-api-auth";

const MAX_STEPS = 100;

export const listStepsKey = (runId: string) => ["steps", "list", runId] as const;

export function useListSteps(runId: string) {
  const { auth, isReady } = useApiAuth();
  return useQuery({
    queryKey: listStepsKey(runId),
    queryFn: () =>
      callApi(listSteps({ auth, body: { run_id: runId, limit: MAX_STEPS } }), zListStepsResponse),
    enabled: isReady,
    select: (data) => data.items,
  });
}
