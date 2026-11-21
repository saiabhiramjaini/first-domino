import type { Diagnosis } from "@/api/generated";

export type StepState = "idle" | "in_range" | "ruled_out" | "first_domino" | "verified_domino";

export type StripDiagnosis = Pick<
  Diagnosis,
  "status" | "search_low" | "search_high" | "first_domino_step" | "verdict_kind"
>;

export function stepState(step: number, diagnosis: StripDiagnosis | undefined): StepState {
  if (!diagnosis || diagnosis.status === "failed") return "idle";
  const { first_domino_step: domino, search_low: low, search_high: high } = diagnosis;
  if (domino !== null) {
    if (step !== domino) return "ruled_out";
    return diagnosis.verdict_kind === "step_verified" ? "verified_domino" : "first_domino";
  }
  if (low === null || high === null) return diagnosis.status === "done" ? "ruled_out" : "idle";
  return step >= low && step <= high ? "in_range" : "ruled_out";
}

export function defaultSelectedStep(
  stepCount: number,
  diagnosis: StripDiagnosis | undefined
): number | null {
  if (stepCount === 0) return null;
  return diagnosis?.first_domino_step ?? diagnosis?.search_low ?? 1;
}
