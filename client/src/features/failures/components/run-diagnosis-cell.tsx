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

// The first domino and verdict of one run's latest diagnosis, for the failures table.
export function RunDiagnosisCell({ diagnosisId }: RunDiagnosisCellProps) {
  const diagnosis = useGetDiagnosis(diagnosisId);
  const now = useNow(isDiagnosisActive(diagnosis.data?.status) ? CLOCK_MS : false);
  if (diagnosisId === null) {
    return <span className="text-xs text-muted-foreground">Not diagnosed</span>;
  }
  if (!diagnosis.data) {
    return diagnosis.isError ? (
      <span className="text-xs text-muted-foreground">Unavailable</span>
    ) : (
      <Skeleton className="h-4 w-40" />
    );
  }
  const data = diagnosis.data;
  if (isWaitingForWorker(data, now)) {
    return <StatusBadge status={{ tone: "warning", label: "Waiting for worker" }} />;
  }
  if (isDiagnosisActive(data.status) || data.status === "failed" || data.verdict_kind === null) {
    return <StatusBadge status={DIAGNOSIS_STATUS[data.status]} />;
  }
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      {data.first_domino_step !== null && (
        <span className="shrink-0 rounded-md border border-domino/30 bg-domino/12 px-1.5 py-0.5 font-mono text-xs text-domino">
          step {data.first_domino_step}
        </span>
      )}
      <span className="truncate text-sm" title={data.explanation?.title}>
        {data.explanation?.title ?? VERDICT_KIND[data.verdict_kind].label}
      </span>
    </div>
  );
}

export function RunVerdictCell({ diagnosisId }: RunDiagnosisCellProps) {
  const diagnosis = useGetDiagnosis(diagnosisId);
  const kind = diagnosis.data?.verdict_kind;
  if (!diagnosis.data || !kind || diagnosis.data.status !== "done") return null;
  const passes = diagnosis.data.verify_passes;
  const samples = diagnosis.data.verify_samples;
  const status =
    kind === "step_verified" && passes !== null && samples !== null
      ? { ...VERDICT_KIND[kind], label: `Proven ${passes}/${samples}` }
      : VERDICT_KIND[kind];
  return <StatusBadge status={status} />;
}
