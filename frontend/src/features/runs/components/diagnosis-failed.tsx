import type { Diagnosis } from "@/api/generated";

type DiagnosisFailedProps = { diagnosis: Diagnosis };

export function DiagnosisFailed({ diagnosis }: DiagnosisFailedProps) {
  return (
    <div
      role="alert"
      className="flex flex-col gap-2 rounded-xl border border-destructive/30 bg-destructive/5 p-4"
    >
      <p className="text-sm font-medium text-destructive">
        The diagnosis stopped before it named a step
      </p>
      <p className="text-sm text-muted-foreground">
        Check that a replay worker is running for this agent and can reach the API, then diagnose
        the run again.
      </p>
      {diagnosis.error_code && (
        <p className="text-xs text-muted-foreground">
          Error code: <span className="font-mono">{diagnosis.error_code}</span>
        </p>
      )}
    </div>
  );
}
