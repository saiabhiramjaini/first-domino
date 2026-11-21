// @vitest-environment node
import { SignJWT } from "jose";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ALERT_TOKEN_AUDIENCE, ALERT_TOKEN_ISSUER } from "@/features/alerts/alert-token";
import { sendEmail } from "@/lib/email";

import { POST } from "./route";

vi.mock("server-only", () => ({}));
vi.mock("@/lib/email", () => ({ sendEmail: vi.fn(async () => true) }));

const SECRET = "alert-test-secret-that-is-long-enough";
const ALERT = {
  to: "owner@example.com",
  cause_id: "6f1c2a8e-4a59-4a51-9d8c-2f7f4f1e9a10",
  title: "Refunded the full amount",
  category: "wrong_entity",
  step_name: "issue_refund",
  summary: "The agent refunded $100 instead of the $20 the policy allows.",
  suggested_fix: "Read the refund limit before issuing a refund.",
  proven: true,
};

async function token(audience = ALERT_TOKEN_AUDIENCE): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  return new SignJWT({})
    .setProtectedHeader({ alg: "HS256" })
    .setIssuer(ALERT_TOKEN_ISSUER)
    .setAudience(audience)
    .setIssuedAt(now)
    .setExpirationTime(now + 300)
    .sign(new TextEncoder().encode(SECRET));
}

function request(body: unknown, bearer?: string): NextRequest {
  return new NextRequest("https://app.test/api/alerts/new-cause", {
    method: "POST",
    headers: bearer ? { authorization: `Bearer ${bearer}` } : {},
    body: JSON.stringify(body),
  });
}

describe("POST /api/alerts/new-cause", () => {
  beforeEach(() => {
    vi.stubEnv("API_JWT_SECRET", SECRET);
    vi.stubEnv("SENDER_EMAIL", "alerts@example.com");
    vi.stubEnv("SENDER_PASS", "app-password");
  });
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.mocked(sendEmail).mockClear();
  });

  it("emails the owner about the new cause, with a link to it", async () => {
    const response = await POST(request(ALERT, await token()));

    expect(response.status).toBe(204);
    expect(sendEmail).toHaveBeenCalledOnce();
    const [sender, email] = vi.mocked(sendEmail).mock.calls[0] ?? [];
    if (!sender || !email) throw new Error("sendEmail was not called");
    expect(sender.user).toBe("alerts@example.com");
    expect(email.to).toBe("owner@example.com");
    expect(email.subject).toBe("New root cause: Refunded the full amount");
    expect(email.text).toContain("Wrong entity · at issue_refund · Proven by replay");
    expect(email.text).toContain(`https://app.test/causes/${ALERT.cause_id}`);
  });

  it("refuses a caller without the API's alert token", async () => {
    const missing = await POST(request(ALERT));
    const sessionToken = await POST(request(ALERT, await token("first-domino-api")));

    expect([missing.status, sessionToken.status]).toEqual([401, 401]);
    expect(sendEmail).not.toHaveBeenCalled();
  });

  it("says so when no sender account is set", async () => {
    vi.stubEnv("SENDER_PASS", "");

    const response = await POST(request(ALERT, await token()));

    expect(response.status).toBe(503);
    expect(sendEmail).not.toHaveBeenCalled();
  });

  it("rejects a malformed alert", async () => {
    const response = await POST(request({ ...ALERT, to: "not-an-email" }, await token()));

    expect(response.status).toBe(400);
  });
});
