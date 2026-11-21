"use client";

import { useInfiniteQuery } from "@tanstack/react-query";

import { listRuns, type ListRunsRequest } from "@/api/generated";
import { zListRunsResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";
import { FIRST_PAGE_CURSOR, nextPageCursor } from "@/lib/paging";

import { useApiAuth } from "./use-api-auth";

export type RunFilters = Omit<ListRunsRequest, "cursor" | "limit">;

export const listRunsKey = (filters: RunFilters) => ["runs", "list", filters] as const;

type ListRunsOptions = { refreshMs?: number | false };

/** Runs, newest first. Pass `refreshMs` to keep the list live (new runs, status changes). */
export function useListRuns(filters: RunFilters, { refreshMs = false }: ListRunsOptions = {}) {
  const { auth, isReady } = useApiAuth();
  return useInfiniteQuery({
    queryKey: listRunsKey(filters),
    queryFn: ({ pageParam }) =>
      callApi(listRuns({ auth, body: { ...filters, cursor: pageParam } }), zListRunsResponse),
    initialPageParam: FIRST_PAGE_CURSOR,
    getNextPageParam: nextPageCursor,
    enabled: isReady,
    refetchInterval: refreshMs,
  });
}
