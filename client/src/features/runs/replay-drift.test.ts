import { describe, expect, it } from "vitest";

import type { Check } from "@/api/generated";

import { driftSummary, driftText, isCalibrating, latestDriftToolName } from "./replay-drift";

function check(index: number, changes: Partial<Check> = {}): Check {
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

describe("driftText", () => {
  it("is empty when every replay matched the recording", () => {
    expect(driftText(check(0))).toBeNull();
  });

  it("counts drifted replays and names the tool when known", () => {
    expect(driftText(check(0, { drifted: 2, drift_tool_name: "lookup_order" }))).toBe(
      "2 drifted · lookup_order"
    );
    expect(driftText(check(0, { drifted: 1 }))).toBe("1 drifted");
  });
});

describe("latestDriftToolName", () => {
  it("takes the tool from the latest check that names one, by index", () => {
    const checks = [
      check(2, { drifted: 1 }),
      check(1, { drifted: 1, drift_tool_name: "get_time" }),
      check(0, { drifted: 1, drift_tool_name: "lookup_order" }),
    ];
    expect(latestDriftToolName(checks)).toBe("get_time");
  });

  it("is null when no check names a tool", () => {
    expect(latestDriftToolName([check(0), check(1, { drifted: 2 })])).toBeNull();
  });
});

describe("driftSummary", () => {
  it("is null when no replay drifted", () => {
    expect(driftSummary([check(0), check(1)])).toBeNull();
  });

  it("adds up drifted replays across every check", () => {
    const checks = [
      check(0, { drifted: 1, drift_tool_name: "lookup_order" }),
      check(1),
      check(2, { drifted: 2 }),
    ];
    expect(driftSummary(checks)).toEqual({ replays: 3, toolName: "lookup_order" });
  });
});

describe("isCalibrating", () => {
  it("is true while the latest check is a pending calibrate check", () => {
    expect(isCalibrating([check(0, { phase: "calibrate", result: "pending" })])).toBe(true);
  });

  it("is false once calibration finished or the search moved on", () => {
    expect(isCalibrating([check(0, { phase: "calibrate", result: "doomed" })])).toBe(false);
    expect(
      isCalibrating([
        check(0, { phase: "calibrate", result: "doomed" }),
        check(1, { phase: "bisect", result: "pending" }),
      ])
    ).toBe(false);
    expect(isCalibrating([])).toBe(false);
  });
});
