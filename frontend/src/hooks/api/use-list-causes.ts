"use client";

import { useInfiniteQuery } from "@tanstack/react-query";

import { listCauses, type ListCausesRequest } from "@/api/generated";
import { zListCausesResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";
import { FIRST_PAGE_CURSOR, nextPageCursor } from "@/lib/paging";

import { useApiAuth } from "./use-api-auth";

export type CauseFilters = Omit<ListCausesRequest, "cursor" | "limit">;

export const listCausesKey = (filters: CauseFilters) => ["causes", "list", filters] as const;

export function useListCauses(filters: CauseFilters) {
  const { auth, isReady } = useApiAuth();
  return useInfiniteQuery({
    queryKey: listCausesKey(filters),
    queryFn: ({ pageParam }) =>
      callApi(listCauses({ auth, body: { ...filters, cursor: pageParam } }), zListCausesResponse),
    initialPageParam: FIRST_PAGE_CURSOR,
    getNextPageParam: nextPageCursor,
    enabled: isReady,
  });
}
