"use client";

import { useInfiniteQuery } from "@tanstack/react-query";

import { listApiKeys } from "@/api/generated";
import { zListApiKeysResponse } from "@/api/generated/zod.gen";
import { callApi } from "@/lib/api-client";
import { FIRST_PAGE_CURSOR, nextPageCursor } from "@/lib/paging";

import { useApiAuth } from "./use-api-auth";

export const listApiKeysKey = () => ["apiKeys", "list"] as const;

export function useListApiKeys() {
  const { auth, isReady } = useApiAuth();
  return useInfiniteQuery({
    queryKey: listApiKeysKey(),
    queryFn: ({ pageParam }) =>
      callApi(listApiKeys({ auth, body: { cursor: pageParam } }), zListApiKeysResponse),
    initialPageParam: FIRST_PAGE_CURSOR,
    getNextPageParam: nextPageCursor,
    enabled: isReady,
  });
}
