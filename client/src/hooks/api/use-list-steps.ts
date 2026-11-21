"use client";

import { useQueries, useQuery } from "@tanstack/react-query";

import { listSteps, type ListStepsResponse, type Step } from "@/api/generated";
import { zListStepsResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { LIVE_REFRESH_MS } from "./diagnosis-activity";
import { useApiAuth } from "./use-api-auth";

const STEPS_PER_PAGE = 100;

export const listStepsKey = (runId: string) => ["steps", "list", runId] as const;

// Every step of a run, page by page: the trace, the step strip and the verdict need them all.
async function fetchSteps(auth: string | undefined, runId: string): Promise<Step[]> {
  const steps: Step[] = [];
  let cursor: string | null = null;
  do {
    const page: ListStepsResponse = await callApi(
      listSteps({ auth, body: { run_id: runId, limit: STEPS_PER_PAGE, cursor } }),
      zListStepsResponse
    );
    steps.push(...page.items);
    cursor = page.next_cursor;
  } while (cursor);
  return steps;
}

type ListStepsOptions = { isLive?: boolean };

/** One run's steps. With `isLive`, new steps appear as the agent records them. */
export function useListSteps(runId: string, { isLive = false }: ListStepsOptions = {}) {
  const { auth, isReady } = useApiAuth();
  return useQuery({
    queryKey: listStepsKey(runId),
    queryFn: () => fetchSteps(auth, runId),
    enabled: isReady,
    refetchInterval: isLive ? LIVE_REFRESH_MS : false,
  });
}

/** The steps of several runs at once, sharing the cache with `useListSteps`. */
export function useListStepsOfRuns(runIds: string[], { isLive = false }: ListStepsOptions = {}) {
  const { auth, isReady } = useApiAuth();
  return useQueries({
    queries: runIds.map((runId) => ({
      queryKey: listStepsKey(runId),
      queryFn: () => fetchSteps(auth, runId),
      enabled: isReady,
      refetchInterval: isLive ? LIVE_REFRESH_MS : false,
    })),
  });
}
