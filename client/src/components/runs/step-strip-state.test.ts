import { describe, expect, it } from "vitest";

import { defaultSelectedStep, stepState, type StripDiagnosis } from "./step-strip-state";

function diagnosis(overrides: Partial<StripDiagnosis>): StripDiagnosis {
  return {
    status: "bisecting",
    search_low: null,
    search_high: null,
    first_domino_step: null,
    verdict_kind: null,
    ...overrides,
  };
}

function strip(stepCount: number, value: StripDiagnosis | undefined) {
  return Array.from({ length: stepCount }, (_, offset) => stepState(offset + 1, value));
}

describe("stepState", () => {
  it("leaves every step idle without a diagnosis", () => {
    expect(strip(3, undefined)).toEqual(["idle", "idle", "idle"]);
  });

  it("leaves steps idle while the diagnosis is queued without a range", () => {
    expect(strip(2, diagnosis({ status: "queued" }))).toEqual(["idle", "idle"]);
  });

  it("leaves steps idle while calibrating, before the search sets a range", () => {
    expect(strip(3, diagnosis({ status: "bisecting" }))).toEqual(["idle", "idle", "idle"]);
  });

  it("marks the search range and rules out the rest while bisecting", () => {
    expect(strip(6, diagnosis({ search_low: 2, search_high: 4 }))).toEqual([
      "ruled_out",
      "in_range",
      "in_range",
      "in_range",
      "ruled_out",
      "ruled_out",
    ]);
  });

  it("shows the first domino before the fix is verified", () => {
    const value = diagnosis({
      status: "verifying",
      search_low: 3,
      search_high: 3,
      first_domino_step: 3,
    });
    expect(strip(4, value)).toEqual(["ruled_out", "ruled_out", "first_domino", "ruled_out"]);
  });

  it("marks the first domino verified once the fix flips the run", () => {
    const value = diagnosis({
      status: "done",
      first_domino_step: 2,
      verdict_kind: "step_verified",
    });
    expect(stepState(2, value)).toBe("verified_domino");
  });

  it("keeps an unverified first domino distinct from a verified one", () => {
    const value = diagnosis({
      status: "done",
      first_domino_step: 2,
      verdict_kind: "multiple_causes",
    });
    expect(stepState(2, value)).toBe("first_domino");
  });

  it("rules out every step when a finished diagnosis names no step", () => {
    const value = diagnosis({ status: "done", verdict_kind: "task_or_tool_issue" });
    expect(strip(2, value)).toEqual(["ruled_out", "ruled_out"]);
  });
});

describe("defaultSelectedStep", () => {
  it("selects the first domino, then the range start, then step 1", () => {
    expect(defaultSelectedStep(5, diagnosis({ first_domino_step: 4, search_low: 2 }))).toBe(4);
    expect(defaultSelectedStep(5, diagnosis({ search_low: 2 }))).toBe(2);
    expect(defaultSelectedStep(5, undefined)).toBe(1);
    expect(defaultSelectedStep(0, undefined)).toBeNull();
  });
});

describe("stepState for a finished diagnosis with several causes", () => {
  it("keeps the suspect range visible when no single step was named", () => {
    const value = diagnosis({
      status: "done",
      verdict_kind: "multiple_causes",
      search_low: 2,
      search_high: 3,
    });
    expect(strip(4, value)).toEqual(["ruled_out", "in_range", "in_range", "ruled_out"]);
  });
});

describe("stepState for a failed diagnosis", () => {
  it("leaves every step neutral, because nothing was concluded", () => {
    const value = diagnosis({ status: "failed", search_low: 1, search_high: 3 });
    expect(strip(3, value)).toEqual(["idle", "idle", "idle"]);
  });
});

describe("stepState once the search has found a step", () => {
  it("marks the found step as the first domino while the fix is verified", () => {
    const value = diagnosis({ status: "verifying", search_low: 3, search_high: 3 });
    expect(strip(4, value)).toEqual(["ruled_out", "ruled_out", "first_domino", "ruled_out"]);
  });

  it("keeps a one-step range as the search range while still bisecting", () => {
    const value = diagnosis({ status: "bisecting", search_low: 3, search_high: 3 });
    expect(stepState(3, value)).toBe("in_range");
  });
});
