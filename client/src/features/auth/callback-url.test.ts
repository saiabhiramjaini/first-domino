import { describe, expect, it } from "vitest";

import { safeCallbackUrl } from "./callback-url";

describe("safeCallbackUrl", () => {
  it("keeps an in-app path", () => {
    expect(safeCallbackUrl("/runs/abc?tab=checks")).toBe("/runs/abc?tab=checks");
  });

  it("falls back for missing, repeated or external values", () => {
    expect(safeCallbackUrl(undefined)).toBe("/runs");
    expect(safeCallbackUrl(["/a", "/b"])).toBe("/runs");
    expect(safeCallbackUrl("https://evil.example")).toBe("/runs");
    expect(safeCallbackUrl("//evil.example")).toBe("/runs");
  });
});
