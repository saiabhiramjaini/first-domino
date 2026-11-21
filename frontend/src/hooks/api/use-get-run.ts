"use client";

import { useQuery } from "@tanstack/react-query";

import { getRun } from "@/api/generated";
import { zGetRunResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { useApiAuth } from "./use-api-auth";

export const getRunKey = (runId: string) => ["runs", "get", runId] as const;

export function useGetRun(runId: string) {
  const { auth, isReady } = useApiAuth();
  return useQuery({
    queryKey: getRunKey(runId),
    queryFn: () => callApi(getRun({ auth, query: { run_id: runId } }), zGetRunResponse),
    enabled: isReady,
    select: (data) => data.run,
  });
}
