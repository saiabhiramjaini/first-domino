import { isApiError } from "@/lib/api-error";

export const TOKEN_REFRESH_COOLDOWN_MS = 30_000;

export function shouldRefreshApiToken(
  error: unknown,
  lastRefreshAt: number | null,
  now: number
): boolean {
  if (!isApiError(error, "unauthenticated")) return false;
  return lastRefreshAt === null || now - lastRefreshAt >= TOKEN_REFRESH_COOLDOWN_MS;
}
