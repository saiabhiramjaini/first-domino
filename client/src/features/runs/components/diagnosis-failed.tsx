import type { Diagnosis } from "@/api/generated";

import { diagnosisErrorCopy } from "../diagnosis-error-copy";

type DiagnosisFailedProps = { diagnosis: Diagnosis; driftToolName: string | null };

export function DiagnosisFailed({ diagnosis, driftToolName }: DiagnosisFailedProps) {
  const copy = diagnosisErrorCopy(diagnosis.error_code, { driftToolName });
  return (
    <div role="alert" className="flex flex-col gap-2 rounded-lg border border-destructive/30 p-4">
      <p className="text-sm font-medium text-destructive">{copy.title}</p>
      <p className="text-sm text-muted-foreground">{copy.fix}</p>
      {copy.code && (
        <pre className="self-start overflow-x-auto rounded-md border bg-card p-3 font-mono text-xs leading-relaxed">
          <code>{copy.code}</code>
        </pre>
      )}
      {diagnosis.error_code && (
        <p className="text-xs text-muted-foreground">
          Error code: <span className="font-mono">{diagnosis.error_code}</span>
        </p>
      )}
    </div>
  );
}
