import type { Diagnosis } from "@/api/generated";

export type StepState = "idle" | "in_range" | "ruled_out" | "first_domino" | "verified_domino";

export type StripDiagnosis = Pick<
  Diagnosis,
  "status" | "search_low" | "search_high" | "first_domino_step" | "verdict_kind"
>;

const FOUND_STEP_STATUSES = [
  "verifying",
  "explaining",
] as const satisfies readonly Diagnosis["status"][];

function foundStep(diagnosis: StripDiagnosis): number | null {
  if (diagnosis.first_domino_step !== null) return diagnosis.first_domino_step;
  const isFound =
    FOUND_STEP_STATUSES.some((status) => status === diagnosis.status) &&
    diagnosis.search_low !== null &&
    diagnosis.search_low === diagnosis.search_high;
  return isFound ? diagnosis.search_low : null;
}

export function stepState(step: number, diagnosis: StripDiagnosis | undefined): StepState {
  if (!diagnosis || diagnosis.status === "failed") return "idle";
  const { search_low: low, search_high: high } = diagnosis;
  const domino = foundStep(diagnosis);
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
