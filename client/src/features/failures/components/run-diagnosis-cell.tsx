"use client";

import { StatusBadge } from "@/components/status/status-badge";
import { DIAGNOSIS_STATUS, VERDICT_KIND } from "@/components/status/status-tones";
import { Skeleton } from "@/components/ui/skeleton";
import { isDiagnosisActive } from "@/hooks/api/diagnosis-activity";
import { useGetDiagnosis } from "@/hooks/api/use-get-diagnosis";
import { useNow } from "@/hooks/use-now";
import { isWaitingForWorker } from "@/features/runs/worker-wait";

const CLOCK_MS = 1_000;

type RunDiagnosisCellProps = { diagnosisId: string | null };

// A failed run's latest diagnosis in one line: the first domino step and what went wrong, or
// how far the search has got.
export function RunDiagnosisCell({ diagnosisId }: RunDiagnosisCellProps) {
  const diagnosis = useGetDiagnosis(diagnosisId);
  const now = useNow(isDiagnosisActive(diagnosis.data?.status) ? CLOCK_MS : false);
  if (diagnosisId === null) {
    return <span className="text-muted-foreground">Not diagnosed</span>;
  }
  if (!diagnosis.data) {
    return diagnosis.isLoadingError ? (
      <span className="text-muted-foreground">Unavailable</span>
    ) : (
      <Skeleton className="h-4 w-40" />
    );
  }
  const data = diagnosis.data;
  if (isWaitingForWorker(data, now)) {
    return <StatusBadge status={{ tone: "warning", label: "Waiting for replay worker" }} />;
  }
  if (isDiagnosisActive(data.status)) {
    return <StatusBadge status={{ tone: "info", label: DIAGNOSIS_STATUS[data.status].label }} />;
  }
  if (data.status === "failed" || data.verdict_kind === null) {
    return <StatusBadge status={DIAGNOSIS_STATUS[data.status]} dot={false} />;
  }
  return (
    <span className="flex min-w-0 items-center gap-2">
      {data.first_domino_step !== null && (
        <span className="shrink-0 font-mono text-xs text-domino">#{data.first_domino_step}</span>
      )}
      <span className="truncate" title={data.explanation?.title}>
        {data.explanation?.title ?? VERDICT_KIND[data.verdict_kind].label}
      </span>
    </span>
  );
}
