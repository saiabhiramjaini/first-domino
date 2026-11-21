import type { CountCausesRequest, CountDiagnosesRequest } from "@/api/generated";
import type { RunFilters } from "@/hooks/api/use-list-runs";

export const RECORDED_RUNS: RunFilters = { sources: ["recorded"] };
export const FAILED_RUNS: RunFilters = { statuses: ["failed"], sources: ["recorded"] };
export const DONE_DIAGNOSES: CountDiagnosesRequest = { statuses: ["done"] };
// Latest only: a run diagnosed again counts once.
export const VERIFIED_DIAGNOSES: CountDiagnosesRequest = {
  verdict_kinds: ["step_verified"],
  latest_only: true,
};
export const ALL_CAUSES: CountCausesRequest = {};
