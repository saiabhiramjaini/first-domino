"use client";

import { useQuery } from "@tanstack/react-query";

import { getLatestBenchmark } from "@/api/generated";
import { zGetLatestBenchmarkResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";

import { useApiAuth } from "./use-api-auth";

export const getLatestBenchmarkKey = () => ["benchmarks", "latest"] as const;

export function useGetLatestBenchmark() {
  const { auth, isReady } = useApiAuth();
  return useQuery({
    queryKey: getLatestBenchmarkKey(),
    queryFn: () => callApi(getLatestBenchmark({ auth }), zGetLatestBenchmarkResponse),
    enabled: isReady,
    select: (data) => data.benchmark,
  });
}
