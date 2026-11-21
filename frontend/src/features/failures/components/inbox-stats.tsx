"use client";

import { StatCard } from "@/components/stats/stat-card";
import { useCountCauses } from "@/hooks/api/use-count-causes";
import { useCountDiagnoses } from "@/hooks/api/use-count-diagnoses";
import { useCountRuns } from "@/hooks/api/use-count-runs";
import { formatInteger } from "@/lib/format";

import { ALL_CAUSES, DONE_DIAGNOSES, FAILED_RUNS, VERIFIED_DIAGNOSES } from "../inbox-filters";

function countText(count: number | undefined, isError: boolean): string | undefined {
  if (isError) return "-";
  return count === undefined ? undefined : formatInteger(count);
}

export function InboxStats() {
  const failedRuns = useCountRuns(FAILED_RUNS);
  const causes = useCountCauses(ALL_CAUSES);
  const diagnosed = useCountDiagnoses(DONE_DIAGNOSES);
  const verified = useCountDiagnoses(VERIFIED_DIAGNOSES);
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <StatCard label="Failed runs" value={countText(failedRuns.data, failedRuns.isError)} />
      <StatCard label="Root causes" value={countText(causes.data, causes.isError)} />
      <StatCard label="Diagnoses done" value={countText(diagnosed.data, diagnosed.isError)} />
      <StatCard
        label="Verified by a fix"
        value={countText(verified.data, verified.isError)}
        hint="The fix flipped the run to passed"
      />
    </div>
  );
}
