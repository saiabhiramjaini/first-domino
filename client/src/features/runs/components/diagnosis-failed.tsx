import type { Diagnosis } from "@/api/generated";

import { diagnosisErrorCopy } from "../diagnosis-error-copy";

type DiagnosisFailedProps = { diagnosis: Diagnosis };

export function DiagnosisFailed({ diagnosis }: DiagnosisFailedProps) {
  const copy = diagnosisErrorCopy(diagnosis.error_code);
  return (
    <div role="alert" className="flex flex-col gap-2 rounded-lg border border-destructive/30 p-4">
      <p className="text-sm font-medium text-destructive">{copy.title}</p>
      <p className="text-sm text-muted-foreground">{copy.fix}</p>
      {diagnosis.error_code && (
        <p className="text-xs text-muted-foreground">
          Error code: <span className="font-mono">{diagnosis.error_code}</span>
        </p>
      )}
    </div>
  );
}
