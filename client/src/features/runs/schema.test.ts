import { describe, expect, it } from "vitest";

import { zFlagRunRequest } from "@/api/generated/zod.gen";

import { FLAG_REASON_MAX, FlagRunSchema } from "./schema";

describe("FlagRunSchema", () => {
  it("trims the reason", () => {
    const parsed = FlagRunSchema.safeParse({ reason: "  The refund was too high  " });
    expect(parsed.success && parsed.data.reason).toBe("The refund was too high");
  });

  it("rejects a blank reason with a readable message", () => {
    const parsed = FlagRunSchema.safeParse({ reason: "   " });
    expect(parsed.success).toBe(false);
    expect(parsed.error?.issues[0]?.message).toBe("Say what went wrong");
  });

  it("caps the reason at the API's limit", () => {
    expect(FLAG_REASON_MAX).toBe(zFlagRunRequest.shape.reason.maxLength);
    expect(FlagRunSchema.safeParse({ reason: "a".repeat(FLAG_REASON_MAX) }).success).toBe(true);
    const parsed = FlagRunSchema.safeParse({ reason: "a".repeat(FLAG_REASON_MAX + 1) });
    expect(parsed.success).toBe(false);
    expect(parsed.error?.issues[0]?.message).toBe("Keep it to 2000 characters or fewer");
  });
});
