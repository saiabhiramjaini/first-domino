"use client";

import { XIcon } from "lucide-react";

import type { Check, Step } from "@/api/generated";
import { QueryError } from "@/components/feedback/query-error";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useListRuns } from "@/hooks/api/use-list-runs";
import { useListStepsOfRuns } from "@/hooks/api/use-list-steps";
import { pageItems } from "@/lib/paging";

import { ReplayComparison, type ReplayLane } from "./replay-comparison";

type CheckReplaysProps = {
  check: Check;
  originalSteps: Step[];
  onClose: () => void;
};

export function CheckReplays({ check, originalSteps, onClose }: CheckReplaysProps) {
  const replays = useListRuns({ check_id: check.id });
  const runs = pageItems(replays.data);
  const steps = useListStepsOfRuns(runs.map((run) => run.id));
  const stepsError = steps.find((query) => query.isError)?.error;
  const lanes: ReplayLane[] = runs.flatMap((run, position) => {
    const runSteps = steps[position]?.data;
    return runSteps ? [{ run, steps: runSteps }] : [];
  });
  const isLoading = replays.isPending || lanes.length < runs.length;

  return (
    <section
      id="check-replays"
      aria-labelledby="check-replays-title"
      className="flex scroll-mt-20 flex-col gap-4 rounded-xl border bg-card p-4"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 id="check-replays-title" className="font-medium">
          Replays of check {check.index}
        </h2>
        <Button variant="ghost" size="icon-sm" aria-label="Close the replays" onClick={onClose}>
          <XIcon />
        </Button>
      </div>
      {replays.isError || stepsError ? (
        <QueryError
          error={replays.error ?? stepsError}
          what="the replays"
          source="runs.load_replays"
          onRetry={() => {
            void replays.refetch();
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
    </section>
  );
}
