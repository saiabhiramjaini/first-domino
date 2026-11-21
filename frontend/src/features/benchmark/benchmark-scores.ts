import type { BenchmarkMethod, BenchmarkScore } from "@/api/generated";

export function barWidthPercent(ratio: number): number {
  if (!Number.isFinite(ratio)) return 0;
  return Math.round(Math.min(1, Math.max(0, ratio)) * 1000) / 10;
}

export function scoreFor(
  scores: readonly BenchmarkScore[],
  method: BenchmarkMethod
): BenchmarkScore | undefined {
  return scores.find((score) => score.method === method);
}
