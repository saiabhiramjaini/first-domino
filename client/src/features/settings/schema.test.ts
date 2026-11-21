import { describe, expect, it } from "vitest";

import { CreateApiKeySchema } from "./schema";

describe("CreateApiKeySchema", () => {
  it("trims the name", () => {
    const parsed = CreateApiKeySchema.safeParse({ name: "  Demo agent  " });
    expect(parsed.success && parsed.data.name).toBe("Demo agent");
  });

  it("rejects a blank name with a readable message", () => {
    const parsed = CreateApiKeySchema.safeParse({ name: "   " });
    expect(parsed.success).toBe(false);
    expect(parsed.error?.issues[0]?.message).toBe("Name is required");
  });

  it("rejects a name over 120 characters", () => {
    expect(CreateApiKeySchema.safeParse({ name: "a".repeat(121) }).success).toBe(false);
    expect(CreateApiKeySchema.safeParse({ name: "a".repeat(120) }).success).toBe(true);
  });
});
