import type { Diagnosis } from "@/api/generated";
import { StatusBadge } from "@/components/status/status-badge";
import { DIAGNOSIS_STATUS } from "@/components/status/status-tones";
import { isDiagnosisActive } from "@/hooks/api/diagnosis-activity";
import { formatInteger, formatUsd } from "@/lib/format";

type DiagnosisProgressProps = { diagnosis: Diagnosis };

function rangeText(diagnosis: Diagnosis): string {
  const { search_low: low, search_high: high, status } = diagnosis;
  if (status === "queued") return "Waiting for a replay worker to pick up the first check.";
  if (low === null || high === null) return "Checking whether a fresh run can succeed at all.";
  if (low === high) return `Narrowed to step ${low}.`;
  return `The first domino is between step ${low} and step ${high}.`;
}

export function DiagnosisProgress({ diagnosis }: DiagnosisProgressProps) {
  const isActive = isDiagnosisActive(diagnosis.status);
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-3">
        {isActive && (
          <span className="relative flex size-2.5" aria-hidden="true">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-search-range opacity-75" />
            <span className="relative inline-flex size-2.5 rounded-full bg-search-range" />
          </span>
        )}
        <StatusBadge status={DIAGNOSIS_STATUS[diagnosis.status]} />
        {isActive && (
          <p className="text-sm text-muted-foreground" aria-live="polite">
            {rangeText(diagnosis)}
          </p>
        )}
      </div>
      <dl className="flex gap-4 text-sm">
        <div className="flex gap-1.5">
          <dt className="text-muted-foreground">Checks</dt>
          <dd className="font-medium tabular-nums">{formatInteger(diagnosis.check_count)}</dd>
        </div>
        <div className="flex gap-1.5">
          <dt className="text-muted-foreground">Replays</dt>
          <dd className="font-medium tabular-nums">{formatInteger(diagnosis.replay_count)}</dd>
        </div>
        <div className="flex gap-1.5">
          <dt className="text-muted-foreground">Cost</dt>
          <dd className="font-medium tabular-nums">{formatUsd(diagnosis.cost_usd)}</dd>
        </div>
      </dl>
    </div>
  );
}
