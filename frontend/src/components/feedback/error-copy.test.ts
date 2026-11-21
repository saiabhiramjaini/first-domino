import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api-error";

import { errorCopy } from "./error-copy";

function apiError(code: ApiError["code"]) {
  return new ApiError({ status: 400, code, title: "t", detail: "d" });
}

describe("errorCopy", () => {
  it("picks the message from the error code", () => {
    expect(errorCopy(apiError("unauthenticated"), "runs").title).toBe("Your session has expired");
    expect(errorCopy(apiError("network_error"), "runs").title).toContain("Could not reach the API");
  });

  it("never shows the raw error text", () => {
    const copy = errorCopy(new Error("secret stack detail"), "runs");
    expect(JSON.stringify(copy)).not.toContain("secret");
  });
});
