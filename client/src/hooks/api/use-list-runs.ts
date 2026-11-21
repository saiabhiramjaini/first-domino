"use client";

import { useInfiniteQuery, useQueries } from "@tanstack/react-query";

import { listRuns, type ListRunsRequest } from "@/api/generated";
import { zListRunsResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";
import { FIRST_PAGE_CURSOR, nextPageCursor } from "@/lib/paging";

import { useApiAuth } from "./use-api-auth";

export type RunFilters = Omit<ListRunsRequest, "cursor" | "limit">;

export const listRunsKey = (filters: RunFilters) => ["runs", "list", filters] as const;

// A check has a handful of replays, so one page holds them all.
const REPLAYS_PER_CHECK = 50;

export const listReplaysKey = (checkId: string) => ["runs", "replays", checkId] as const;

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

function fetchReplays(auth: string | undefined, checkId: string) {
  return callApi(
    listRuns({ auth, body: { check_id: checkId, limit: REPLAYS_PER_CHECK } }),
    zListRunsResponse
  );
}

/** The replay runs of each check, one query per check, in the order given. */
export function useListReplaysOfChecks(checkIds: string[]) {
  const { auth, isReady } = useApiAuth();
  return useQueries({
    queries: checkIds.map((checkId) => ({
      queryKey: listReplaysKey(checkId),
      queryFn: () => fetchReplays(auth, checkId),
      enabled: isReady,
      select: (data: Awaited<ReturnType<typeof fetchReplays>>) => data.items,
    })),
  });
}
