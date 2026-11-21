"use client";

import { MetricStrip } from "@/components/stats/metric-strip";
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
    <MetricStrip
      metrics={[
        {
          label: "Failed runs",
          value: countText(failedRuns.data, failedRuns.isError),
          hint: "Recorded runs your check failed",
        },
        {
          label: "Diagnosed",
          value: countText(diagnosed.data, diagnosed.isError),
          hint: "Searched to the first domino",
        },
        {
          label: "Proven by a fix",
          value: countText(verified.data, verified.isError),
          hint: "The fixed step made the run pass",
          tone: "verified",
        },
        {
          label: "Root causes",
          value: countText(causes.data, causes.isError),
          hint: "Distinct causes across runs",
          tone: "domino",
        },
      ]}
    />
  );
}
