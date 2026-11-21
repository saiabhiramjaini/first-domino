import type { Run } from "@/api/generated";

type FlaggableRun = Pick<Run, "source" | "status" | "finished_at">;

/** Only a finished recorded run that passed can be flagged; the API answers 409 otherwise. */
export function canFlagRun(run: FlaggableRun): boolean {
  return run.source === "recorded" && run.status === "passed" && run.finished_at !== null;
}

export type FailureReason = { label: string; reason: string; flaggedAt: string | null };

type ReasonRun = Pick<Run, "status" | "failure_reason" | "flagged_at">;

/** Why a failed run failed, from whoever flagged it or from the customer's code. */
export function failureReason(run: ReasonRun): FailureReason | null {
  if (run.status !== "failed" || !run.failure_reason) return null;
  return {
    label: run.flagged_at === null ? "Reason" : "Flagged as failed",
    reason: run.failure_reason,
    flaggedAt: run.flagged_at,
  };
}

/** A flagged run's replays are judged by a model against its reason, not by the success check. */
export function isJudgedByModel(run: Pick<Run, "flagged_at">, diagnosisId: string | null): boolean {
  return run.flagged_at !== null && diagnosisId !== null;
}
