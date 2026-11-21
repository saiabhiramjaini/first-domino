import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api-error";

import { TOKEN_REFRESH_COOLDOWN_MS, shouldRefreshApiToken } from "./token-refresh";

const unauthenticated = new ApiError({
  status: 401,
  code: "unauthenticated",
  title: "Sign in",
  detail: "Token rejected",
});

describe("shouldRefreshApiToken", () => {
  it("refreshes on the first rejected token", () => {
    expect(shouldRefreshApiToken(unauthenticated, null, 1_000)).toBe(true);
  });

  it("waits for the cooldown before trying again", () => {
    expect(shouldRefreshApiToken(unauthenticated, 1_000, 2_000)).toBe(false);
    expect(shouldRefreshApiToken(unauthenticated, 1_000, 1_000 + TOKEN_REFRESH_COOLDOWN_MS)).toBe(
      true
    );
  });

  it("ignores every other error", () => {
    const notFound = new ApiError({ status: 404, code: "not_found", title: "t", detail: "d" });
    expect(shouldRefreshApiToken(notFound, null, 1_000)).toBe(false);
    expect(shouldRefreshApiToken(new Error("boom"), null, 1_000)).toBe(false);
  });
});
