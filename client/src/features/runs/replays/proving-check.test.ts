import { describe, expect, it } from "vitest";

import type { Check } from "@/api/generated";

import { provingCheck } from "./proving-check";

function check(index: number, changes: Partial<Check>): Check {
  return {
    id: `check-${index}`,
    diagnosis_id: "d",
    index,
    phase: "bisect",
    save_point: 1,
    samples: 3,
    passes: 0,
    result: "doomed",
    drifted: 0,
    drift_tool_name: null,
    created_at: "2026-11-21T00:00:00Z",
    finished_at: "2026-11-21T00:00:01Z",
    ...changes,
  };
}

describe("provingCheck", () => {
  it("picks the passing verify check that rewrote the first domino", () => {
    const checks = [
      check(0, { phase: "bisect", save_point: 2 }),
      check(1, { phase: "verify", save_point: 1, result: "can_succeed", passes: 3 }),
    ];

    expect(provingCheck(checks, 2)?.id).toBe("check-1");
  });

  it("ignores fixes of other steps and fixes that did not pass", () => {
    const checks = [
      check(0, { phase: "verify", save_point: 1, result: "doomed" }),
      check(1, { phase: "fallback", save_point: 3, result: "can_succeed" }),
    ];

    expect(provingCheck(checks, 2)).toBeNull();
    expect(provingCheck(checks, null)).toBeNull();
  });
});
