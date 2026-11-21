"use client";

import { useSession } from "next-auth/react";

export type ApiAuth = { auth: string | undefined; isReady: boolean };

export function useApiAuth(): ApiAuth {
  const { data, status } = useSession();
  const token = data?.apiToken;
  return { auth: token, isReady: status === "authenticated" && Boolean(token) };
}
