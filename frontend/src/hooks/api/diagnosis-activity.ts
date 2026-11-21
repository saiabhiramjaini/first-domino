import type { DiagnosisStatus } from "@/api/generated";

const FINISHED_STATUSES = ["done", "failed"] as const satisfies readonly DiagnosisStatus[];

export const LIVE_REFRESH_MS = 1_000;

export function isDiagnosisActive(status: DiagnosisStatus | undefined): boolean {
  return status !== undefined && !FINISHED_STATUSES.some((finished) => finished === status);
}
