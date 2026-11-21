"use client";

import { useQuery } from "@tanstack/react-query";

import { getCause } from "@/api/generated";
import { zGetCauseResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { useApiAuth } from "./use-api-auth";

export const getCauseKey = (causeId: string) => ["causes", "get", causeId] as const;

export function useGetCause(causeId: string) {
  const { auth, isReady } = useApiAuth();
  return useQuery({
    queryKey: getCauseKey(causeId),
    queryFn: () => callApi(getCause({ auth, query: { cause_id: causeId } }), zGetCauseResponse),
    enabled: isReady,
    select: (data) => data.cause,
  });
}
