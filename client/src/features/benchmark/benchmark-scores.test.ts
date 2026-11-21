import { describe, expect, it } from "vitest";

import type { BenchmarkScore } from "@/api/generated";

import { barWidthPercent, scoreFor } from "./benchmark-scores";

function score(method: BenchmarkScore["method"], exact: number): BenchmarkScore {
  return {
    method,
    runs_scored: 40,
    exact_accuracy: exact,
    within_one_accuracy: exact,
    verified_rate: null,
    mean_cost_usd: 0.1,
    mean_seconds: 30,
  };
}

describe("barWidthPercent", () => {
  it("turns a ratio into a percent width", () => {
    expect(barWidthPercent(0.836)).toBe(83.6);
  });

  it("clamps values outside 0 to 1", () => {
    expect(barWidthPercent(-0.2)).toBe(0);
    expect(barWidthPercent(1.4)).toBe(100);
    expect(barWidthPercent(Number.NaN)).toBe(0);
  });
});

describe("scoreFor", () => {
  it("finds the score of one method", () => {
    const scores = [score("read_trace_judge", 0.4), score("first_domino", 0.8)];
    expect(scoreFor(scores, "first_domino")?.exact_accuracy).toBe(0.8);
    expect(scoreFor([], "first_domino")).toBeUndefined();
  });
});
