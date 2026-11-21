import { describe, expect, it } from "vitest";

import { stepSummary } from "./trace-summary";

describe("stepSummary", () => {
  it("shows the first tool call like a function call", () => {
    expect(
      stepSummary({
        role: "assistant",
        content: null,
        tool_calls: [{ id: "c1", name: "check_calendar", arguments: '{"date":"2026-11-22"}' }],
      })
    ).toBe('check_calendar(date="2026-11-22")');
  });

  it("falls back to the text, cut to one line", () => {
    const summary = stepSummary({ role: "assistant", content: `done ${"x".repeat(200)}` });
    expect(summary.length).toBe(110);
    expect(summary.endsWith("…")).toBe(true);
  });
});
