import { describe, expect, it } from "vitest";

import { canFlagRun, failureReason, isJudgedByModel } from "./run-flag";

const FINISHED = "2026-11-22T11:00:00Z";

describe("canFlagRun", () => {
  it("allows a finished recorded run that passed", () => {
    expect(canFlagRun({ source: "recorded", status: "passed", finished_at: FINISHED })).toBe(true);
  });

  it("refuses a replay, an unfinished run and any other status", () => {
    expect(canFlagRun({ source: "replay", status: "passed", finished_at: FINISHED })).toBe(false);
    expect(canFlagRun({ source: "recorded", status: "passed", finished_at: null })).toBe(false);
    for (const status of ["running", "failed", "errored"] as const) {
      expect(canFlagRun({ source: "recorded", status, finished_at: FINISHED })).toBe(false);
    }
  });
});

describe("failureReason", () => {
  it("labels a flagged run's reason and keeps when it was flagged", () => {
    const reason = failureReason({
      status: "failed",
      failure_reason: "Refund was too high",
      flagged_at: FINISHED,
    });
    expect(reason).toEqual({
      label: "Flagged as failed",
      reason: "Refund was too high",
      flaggedAt: FINISHED,
    });
  });

  it("shows the reason the customer's code gave", () => {
    const reason = failureReason({
      status: "failed",
      failure_reason: "Wrong currency",
      flagged_at: null,
    });
    expect(reason).toEqual({ label: "Reason", reason: "Wrong currency", flaggedAt: null });
  });

  it("shows nothing without a reason or on a run that did not fail", () => {
    expect(failureReason({ status: "failed", failure_reason: null, flagged_at: null })).toBe(null);
    expect(failureReason({ status: "failed", failure_reason: "", flagged_at: null })).toBe(null);
    expect(failureReason({ status: "passed", failure_reason: "x", flagged_at: null })).toBe(null);
  });
});

describe("isJudgedByModel", () => {
  it("is true only for a flagged run with a diagnosis", () => {
    expect(isJudgedByModel({ flagged_at: FINISHED }, "diagnosis-1")).toBe(true);
    expect(isJudgedByModel({ flagged_at: FINISHED }, null)).toBe(false);
    expect(isJudgedByModel({ flagged_at: null }, "diagnosis-1")).toBe(false);
  });
});
