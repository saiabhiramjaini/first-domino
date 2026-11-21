"use client";

import { XIcon } from "lucide-react";

import type { Step } from "@/api/generated";
import { QueryError } from "@/components/feedback/query-error";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useListReplaysOfChecks } from "@/hooks/api/use-list-runs";
import { useListStepsOfRuns } from "@/hooks/api/use-list-steps";

import type { CheckRow } from "../components/check-rows";
import { ReplayComparison, type ReplayLane } from "./replay-comparison";

type CheckReplaysProps = {
  check: CheckRow;
  // While the diagnosis runs, new replays and their steps keep arriving.
  isLive: boolean;
  originalSteps: Step[];
  onClose: () => void;
};

export function CheckReplays({ check, isLive, originalSteps, onClose }: CheckReplaysProps) {
  // Every round of the row: a rechecked save point shows all its replays together.
  const replays = useListReplaysOfChecks(
    check.rounds.map((round) => round.id),
    { isLive }
  );
  const replaysError = replays.find((query) => query.isLoadingError)?.error;
  const runs = replays.flatMap((query) => query.data ?? []);
  const steps = useListStepsOfRuns(
    runs.map((run) => run.id),
    { isLive: isLive || runs.some((run) => run.status === "running") }
  );
  const stepsError = steps.find((query) => query.isLoadingError)?.error;
  const lanes: ReplayLane[] = runs.flatMap((run, position) => {
    const runSteps = steps[position]?.data;
    return runSteps ? [{ run, steps: runSteps }] : [];
  });
  const isLoading = replays.some((query) => query.isPending) || lanes.length < runs.length;

  return (
    <section
      id="check-replays"
      aria-labelledby="check-replays-title"
      className="flex scroll-mt-20 flex-col rounded-lg border"
    >
      <div className="flex items-center justify-between gap-2 border-b px-4 py-3">
        <h2 id="check-replays-title" className="text-sm font-semibold">
          Replays of check <span className="font-mono">#{check.number}</span>
        </h2>
        <Button variant="ghost" size="icon-sm" aria-label="Close the replays" onClick={onClose}>
          <XIcon />
        </Button>
      </div>
      <div className="p-4">
        {replaysError || stepsError ? (
          <QueryError
            error={replaysError ?? stepsError}
            what="the replays"
            source="runs.load_replays"
            onRetry={() => {
              for (const query of replays) if (query.isError) void query.refetch();
              for (const query of steps) if (query.isError) void query.refetch();
            }}
          />
        ) : isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : runs.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No replays recorded for this check yet. They appear once the replay worker runs them.
          </p>
        ) : (
          <ReplayComparison check={check} originalSteps={originalSteps} replays={lanes} />
        )}
      </div>
    </section>
  );
}
