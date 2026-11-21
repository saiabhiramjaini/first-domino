"use client";

import { MetricStrip } from "@/components/stats/metric-strip";
import { useCountCauses } from "@/hooks/api/use-count-causes";
import { useCountDiagnoses } from "@/hooks/api/use-count-diagnoses";
import { useCountRuns } from "@/hooks/api/use-count-runs";
import { formatInteger } from "@/lib/format";

import { ALL_CAUSES, FAILED_RUNS, RECORDED_RUNS, VERIFIED_DIAGNOSES } from "../inbox-filters";

const REFRESH_MS = 5_000;

function countText(count: number | undefined, isError: boolean): string | undefined {
  if (isError) return "-";
  return count === undefined ? undefined : formatInteger(count);
}

// The four numbers above the runs list.
export function InboxStats() {
  const runs = useCountRuns(RECORDED_RUNS, { refreshMs: REFRESH_MS });
  const failedRuns = useCountRuns(FAILED_RUNS, { refreshMs: REFRESH_MS });
  const verified = useCountDiagnoses(VERIFIED_DIAGNOSES, { refreshMs: REFRESH_MS });
  const causes = useCountCauses(ALL_CAUSES, { refreshMs: REFRESH_MS });
  return (
    <MetricStrip
      metrics={[
        { label: "Runs", value: countText(runs.data, runs.isLoadingError) },
        { label: "Failed", value: countText(failedRuns.data, failedRuns.isLoadingError) },
        { label: "First domino proven", value: countText(verified.data, verified.isLoadingError) },
        { label: "Root causes", value: countText(causes.data, causes.isLoadingError) },
      ]}
    />
  );
}
