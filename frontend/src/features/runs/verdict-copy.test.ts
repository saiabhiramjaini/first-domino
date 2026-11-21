import { describe, expect, it } from "vitest";

import { zVerdictKind } from "@/api/generated/zod.gen";

import { verdictCopy } from "./verdict-copy";

const base = { first_domino_step: null, search_low: null, search_high: null };

describe("verdictCopy", () => {
  it("has a headline for every verdict kind", () => {
    for (const kind of zVerdictKind.options) {
      expect(verdictCopy({ ...base, verdict_kind: kind })?.headline).toBeTruthy();
    }
  });

  it("names the first domino step", () => {
    const copy = verdictCopy({ ...base, verdict_kind: "step_verified", first_domino_step: 7 });
    expect(copy?.headline).toBe("Step 7 is the first domino");
  });

  it("names the suspect range for multiple causes", () => {
    const copy = verdictCopy({
      ...base,
      verdict_kind: "multiple_causes",
      search_low: 9,
      search_high: 12,
    });
    expect(copy?.body).toContain("steps 9 to 12");
  });

  it("has no copy before a verdict exists", () => {
    expect(verdictCopy({ ...base, verdict_kind: null })).toBeNull();
  });
});
