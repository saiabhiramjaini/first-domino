"use client";

import { useQuery } from "@tanstack/react-query";

import { countRuns, type CountRunsRequest } from "@/api/generated";
import { zCountRunsResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { useApiAuth } from "./use-api-auth";

export const countRunsKey = (filters: CountRunsRequest) => ["runs", "count", filters] as const;

export function useCountRuns(filters: CountRunsRequest) {
  const { auth, isReady } = useApiAuth();
  return useQuery({
    queryKey: countRunsKey(filters),
    queryFn: () => callApi(countRuns({ auth, body: filters }), zCountRunsResponse),
    enabled: isReady,
    select: (data) => data.count,
  });
}
