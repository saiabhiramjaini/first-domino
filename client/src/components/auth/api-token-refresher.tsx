"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { useEffect } from "react";

import { reportClientError } from "@/lib/report-client-error";

import { shouldRefreshApiToken } from "./token-refresh";

// The API rejects a token signed with an old secret until it would expire; asking NextAuth
// for an `update` re-signs it, so a rejected call re-signs once and refetches.
export function ApiTokenRefresher() {
  const queryClient = useQueryClient();
  const { update } = useSession();

  useEffect(() => {
    let lastRefreshAt: number | null = null;

    function handleError(error: unknown) {
      const now = Date.now();
      if (!shouldRefreshApiToken(error, lastRefreshAt, now)) return;
      lastRefreshAt = now;
      update()
        .then(() => queryClient.invalidateQueries())
        .catch((refreshError: unknown) => reportClientError(refreshError, "auth.refresh_token"));
    }

    const unsubscribeQueries = queryClient.getQueryCache().subscribe((event) => {
      if (event.type === "updated" && event.action.type === "error") {
        handleError(event.action.error);
      }
    });
    const unsubscribeMutations = queryClient.getMutationCache().subscribe((event) => {
      if (event.type === "updated" && event.action.type === "error") {
        handleError(event.action.error);
      }
    });
    return () => {
      unsubscribeQueries();
      unsubscribeMutations();
    };
  }, [queryClient, update]);

  return null;
}
