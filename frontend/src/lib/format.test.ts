import { describe, expect, it } from "vitest";

import { formatCount, formatPercent, formatRelative, formatUsd } from "./format";

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

describe("formatCount", () => {
  it("uses the singular for one and the plural otherwise", () => {
    const noun = { one: "run", other: "runs" };
    expect(formatCount(1, noun)).toBe("1 run");
    expect(formatCount(0, noun)).toBe("0 runs");
    expect(formatCount(1200, noun)).toBe("1,200 runs");
  });
});
