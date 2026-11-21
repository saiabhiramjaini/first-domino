"use client";

import { useQuery } from "@tanstack/react-query";

import { getProjectSelf } from "@/api/generated";
import { zGetProjectSelfResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { useApiAuth } from "./use-api-auth";

export const getProjectSelfKey = () => ["projects", "self"] as const;

export function useGetProjectSelf() {
  const { auth, isReady } = useApiAuth();
  return useQuery({
    queryKey: getProjectSelfKey(),
    queryFn: () => callApi(getProjectSelf({ auth }), zGetProjectSelfResponse),
    enabled: isReady,
    select: (data) => data.project,
  });
}
