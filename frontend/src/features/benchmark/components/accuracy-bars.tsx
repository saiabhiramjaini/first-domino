import type { BenchmarkMethod, BenchmarkScore } from "@/api/generated";
import { BENCHMARK_METHOD_LABEL } from "@/components/status/status-tones";
import { formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";

import { barWidthPercent } from "../benchmark-scores";

const METHOD_BAR_CLASS = {
  first_domino: "bg-domino",
  read_trace_judge: "bg-muted-foreground/40",
} as const satisfies Record<BenchmarkMethod, string>;

type AccuracyBarsProps = { scores: readonly BenchmarkScore[] };

export function AccuracyBars({ scores }: AccuracyBarsProps) {
  return (
    <ul className="flex flex-col gap-4" aria-label="Exact step accuracy by method">
      {scores.map((score) => (
        <li key={score.method} className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between gap-2 text-sm">
            <span className="font-medium">{BENCHMARK_METHOD_LABEL[score.method]}</span>
            <span className="tabular-nums">{formatPercent(score.exact_accuracy)}</span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
            <div
              className={cn("h-full rounded-full", METHOD_BAR_CLASS[score.method])}
              style={{ width: `${barWidthPercent(score.exact_accuracy)}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
