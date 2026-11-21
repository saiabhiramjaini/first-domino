"use client";

import { useInfiniteQuery } from "@tanstack/react-query";

import { listDiagnoses, type ListDiagnosesRequest } from "@/api/generated";
import { zListDiagnosesResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";
import { FIRST_PAGE_CURSOR, nextPageCursor } from "@/lib/paging";

import { useApiAuth } from "./use-api-auth";

export type DiagnosisFilters = Omit<ListDiagnosesRequest, "cursor" | "limit">;

export const listDiagnosesKey = (filters: DiagnosisFilters) =>
  ["diagnoses", "list", filters] as const;

export function useListDiagnoses(filters: DiagnosisFilters) {
  const { auth, isReady } = useApiAuth();
  return useInfiniteQuery({
    queryKey: listDiagnosesKey(filters),
    queryFn: ({ pageParam }) =>
      callApi(
        listDiagnoses({ auth, body: { ...filters, cursor: pageParam } }),
        zListDiagnosesResponse
      ),
    initialPageParam: FIRST_PAGE_CURSOR,
    getNextPageParam: nextPageCursor,
    enabled: isReady,
  });
}
