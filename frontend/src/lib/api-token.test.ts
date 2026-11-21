// @vitest-environment node
import { jwtVerify } from "jose";
import { describe, expect, it } from "vitest";

import {
  API_TOKEN_AUDIENCE,
  API_TOKEN_ISSUER,
  apiTokenNeedsRefresh,
  mintApiToken,
} from "./api-token";

const SECRET = "test-secret-that-is-long-enough-for-hs256";
const NOW = 1_800_000_000;

describe("mintApiToken", () => {
  it("signs the claims the API verifies", async () => {
    const { token, expiresAt } = await mintApiToken(
      { googleId: "google-123", email: "a@example.com", name: "Ada" },
      SECRET,
      NOW
    );
    const { payload, protectedHeader } = await jwtVerify(token, new TextEncoder().encode(SECRET), {
      issuer: API_TOKEN_ISSUER,
      audience: API_TOKEN_AUDIENCE,
      currentDate: new Date(NOW * 1000),
    });
    expect(protectedHeader.alg).toBe("HS256");
    expect(payload).toMatchObject({
      sub: "google-123",
      email: "a@example.com",
      name: "Ada",
      iat: NOW,
      exp: NOW + 3600,
    });
    expect(expiresAt).toBe(NOW + 3600);
  });
});

describe("apiTokenNeedsRefresh", () => {
  it("refreshes a missing token", () => {
    expect(apiTokenNeedsRefresh(undefined, NOW)).toBe(true);
  });

  it("keeps a token with more than five minutes left", () => {
    expect(apiTokenNeedsRefresh(NOW + 301, NOW)).toBe(false);
  });

  it("refreshes a token with less than five minutes left", () => {
    expect(apiTokenNeedsRefresh(NOW + 299, NOW)).toBe(true);
  });
});
