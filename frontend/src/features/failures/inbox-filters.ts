import type { CountCausesRequest, CountDiagnosesRequest } from "@/api/generated";
import type { RunFilters } from "@/hooks/api/use-list-runs";

export const FAILED_RUNS: RunFilters = { statuses: ["failed"], sources: ["recorded"] };
export const DONE_DIAGNOSES: CountDiagnosesRequest = { statuses: ["done"] };
export const VERIFIED_DIAGNOSES: CountDiagnosesRequest = { verdict_kinds: ["step_verified"] };
export const ALL_CAUSES: CountCausesRequest = {};
export const TOP_CAUSE_COUNT = 5;
