"use client";

import { useQueries, useQuery } from "@tanstack/react-query";

import { listSteps } from "@/api/generated";
import { zListStepsResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { LIVE_REFRESH_MS } from "./diagnosis-activity";
import { useApiAuth } from "./use-api-auth";

const MAX_STEPS = 100;

export const listStepsKey = (runId: string) => ["steps", "list", runId] as const;

function fetchSteps(auth: string | undefined, runId: string) {
  return callApi(
    listSteps({ auth, body: { run_id: runId, limit: MAX_STEPS } }),
    zListStepsResponse
  );
}

type ListStepsOptions = { isLive?: boolean };

/** One run's steps. With `isLive`, new steps appear as the agent records them. */
export function useListSteps(runId: string, { isLive = false }: ListStepsOptions = {}) {
  const { auth, isReady } = useApiAuth();
  return useQuery({
    queryKey: listStepsKey(runId),
    queryFn: () => fetchSteps(auth, runId),
    enabled: isReady,
    select: (data) => data.items,
    refetchInterval: isLive ? LIVE_REFRESH_MS : false,
  });
}

/** The steps of several runs at once, sharing the cache with `useListSteps`. */
export function useListStepsOfRuns(runIds: string[]) {
  const { auth, isReady } = useApiAuth();
  return useQueries({
    queries: runIds.map((runId) => ({
      queryKey: listStepsKey(runId),
      queryFn: () => fetchSteps(auth, runId),
      enabled: isReady,
      select: (data: Awaited<ReturnType<typeof fetchSteps>>) => data.items,
    })),
  });
}
