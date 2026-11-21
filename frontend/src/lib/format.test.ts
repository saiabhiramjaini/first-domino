import { describe, expect, it } from "vitest";

import { formatPercent, formatRelative, formatUsd } from "./format";

describe("format", () => {
  it("formats a past time relative to now", () => {
    const now = new Date("2026-11-21T12:00:00Z");
    expect(formatRelative("2026-11-21T11:58:00Z", now)).toBe("2 minutes ago");
    expect(formatRelative("2026-11-20T12:00:00Z", now)).toBe("yesterday");
  });

  it("formats ratios and money", () => {
    expect(formatPercent(0.836)).toBe("84%");
    expect(formatUsd(0.0123)).toBe("$0.0123");
  });
});
