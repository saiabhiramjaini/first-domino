import { describe, expect, it } from "vitest";

import { stepState } from "@/components/runs/step-strip-state";

import { DEMO_FIRST_DOMINO, DEMO_FRAMES, DEMO_STEP_COUNT } from "./bisect-demo-frames";

describe("DEMO_FRAMES", () => {
  it("narrows the search range on every bisect frame", () => {
    const widths = DEMO_FRAMES.flatMap((frame) => {
      const low = frame.diagnosis?.search_low;
      const high = frame.diagnosis?.search_high;
      return low == null || high == null ? [] : [high - low];
    });
    expect(widths).toEqual([...widths].sort((a, b) => b - a));
    expect(new Set(widths).size).toBe(widths.length - 1);
  });

  it("keeps the first domino inside every search range", () => {
    for (const frame of DEMO_FRAMES) {
      const low = frame.diagnosis?.search_low;
      const high = frame.diagnosis?.search_high;
      if (low == null || high == null) continue;
      expect(DEMO_FIRST_DOMINO).toBeGreaterThanOrEqual(low);
      expect(DEMO_FIRST_DOMINO).toBeLessThanOrEqual(high);
      expect(high).toBeLessThanOrEqual(DEMO_STEP_COUNT);
    }
  });

  it("ends with the first domino verified", () => {
    const last = DEMO_FRAMES.at(-1);
    expect(stepState(DEMO_FIRST_DOMINO, last?.diagnosis)).toBe("verified_domino");
  });

  it("has unique frame ids", () => {
    expect(new Set(DEMO_FRAMES.map((frame) => frame.id)).size).toBe(DEMO_FRAMES.length);
  });
});
