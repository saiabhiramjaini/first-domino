"use client";

import { EmptyState } from "@/components/feedback/empty-state";
import { QueryError } from "@/components/feedback/query-error";
import { StatCard } from "@/components/stats/stat-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useGetLatestBenchmark } from "@/hooks/api/use-get-latest-benchmark";
import { formatDateTime, formatInteger, formatPercent, formatUsd } from "@/lib/format";

import { scoreFor } from "../benchmark-scores";
import { AccuracyBars } from "./accuracy-bars";
import { BenchmarkTable } from "./benchmark-table";

export function BenchmarkOverview() {
  const benchmark = useGetLatestBenchmark();

  if (benchmark.isPending) {
    return (
      <div className="flex flex-col gap-6" aria-busy="true">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
        </div>
        <Skeleton className="h-40 w-full rounded-xl" />
      </div>
    );
  }

  if (benchmark.isError) {
    return (
      <QueryError
        error={benchmark.error}
        what="the benchmark"
        source="benchmark.latest"
        onRetry={() => benchmark.refetch()}
      />
    );
  }

  if (benchmark.data === null) {
    return (
      <EmptyState
        title="No benchmark yet"
        description="The benchmark replays labelled failed runs with First Domino and with an LLM judge reading the trace. Its latest results appear here once it has run."
      />
    );
  }

  const { scores, created_at: createdAt } = benchmark.data;
  const firstDomino = scoreFor(scores, "first_domino");
  const baseline = scoreFor(scores, "read_trace_judge");

  return (
    <div className="flex flex-col gap-6">
      {firstDomino && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Exact step found"
            value={formatPercent(firstDomino.exact_accuracy)}
            hint={baseline ? `Trace judge: ${formatPercent(baseline.exact_accuracy)}` : undefined}
          />
          <StatCard
            label="Within one step"
            value={formatPercent(firstDomino.within_one_accuracy)}
            hint={
              baseline ? `Trace judge: ${formatPercent(baseline.within_one_accuracy)}` : undefined
            }
          />
          <StatCard
            label="Proven by replay"
            value={
              firstDomino.verified_rate === null
                ? "No proof"
                : formatPercent(firstDomino.verified_rate)
            }
            hint="The trace judge cannot prove its answer"
          />
          <StatCard
            label="Mean cost per run"
            value={formatUsd(firstDomino.mean_cost_usd)}
            hint={baseline ? `Trace judge: ${formatUsd(baseline.mean_cost_usd)}` : undefined}
          />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Exact first domino accuracy</CardTitle>
          <CardDescription>
            How often each method names the exact step that doomed the run.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AccuracyBars scores={scores} />
        </CardContent>
      </Card>

      <section className="flex flex-col gap-3" aria-labelledby="benchmark-table-title">
        <div className="flex flex-col gap-1">
          <h2 id="benchmark-table-title" className="text-lg font-semibold">
            All numbers
          </h2>
          <p className="text-sm text-muted-foreground">
            {firstDomino ? `${formatInteger(firstDomino.runs_scored)} labelled runs. ` : ""}
            Run on {formatDateTime(createdAt)}.
          </p>
        </div>
        <BenchmarkTable scores={scores} />
      </section>
    </div>
  );
}
