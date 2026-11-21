import type { Diagnosis, VerdictKind } from "@/api/generated";

export type VerdictCopy = { headline: string; body: string };

type VerdictInput = Pick<
  Diagnosis,
  "verdict_kind" | "first_domino_step" | "search_low" | "search_high"
>;

function stepLabel(step: number | null): string {
  return step === null ? "One step" : `Step ${step}`;
}

function rangeLabel(low: number | null, high: number | null): string {
  if (low === null || high === null) return "the steps around it";
  if (low === high) return `step ${low}`;
  return `steps ${low} to ${high}`;
}

const COPY = {
  step_verified: (input) => ({
    headline: `${stepLabel(input.first_domino_step)} is the first domino`,
    body: "Replays from just before it can still succeed, every replay from it fails, and rewriting this one step flipped the run from failed to passed.",
  }),
  step_unverified: (input) => ({
    headline: `${stepLabel(input.first_domino_step)} is the likely first domino`,
    body: "Replays from just before it can still succeed and every replay from it fails, but the rewritten step did not pass often enough to prove the fix. Treat it as the best lead, not a proof.",
  }),
  multiple_causes: (input) => ({
    headline: "No single step flips this run",
    body: `Fixing ${rangeLabel(input.search_low, input.search_high)} one at a time never made the run pass. More than one step went wrong, so fix them together and record a new run.`,
  }),
  task_or_tool_issue: () => ({
    headline: "Even a fresh run fails",
    body: "No replay succeeded, even when the agent started again from the task alone. Look at the task, the tools or the success check rather than at one agent step.",
  }),
} as const satisfies Record<VerdictKind, (input: VerdictInput) => VerdictCopy>;

export function verdictCopy(input: VerdictInput): VerdictCopy | null {
  return input.verdict_kind === null ? null : COPY[input.verdict_kind](input);
}
