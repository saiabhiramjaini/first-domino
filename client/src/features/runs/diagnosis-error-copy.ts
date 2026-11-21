import type { DiagnosisErrorCode } from "@/api/generated";

// `code` is a snippet to show next to the fix, when the fix is a change to the agent's code.
export type DiagnosisErrorCopy = { title: string; fix: string; code?: string };

// What the checks tell about the failure: the tool that returned different data on replay.
export type DiagnosisErrorContext = { driftToolName: string | null };

const COPY = {
  replay_unavailable: () => ({
    title: "No replay came back",
    fix: "Every replay of a check errored or timed out. Start a replay worker for this agent with fd.Worker, check it can reach the API, then diagnose the run again.",
  }),
  check_budget_exceeded: () => ({
    title: "The diagnosis ran out of checks",
    fix: "The search needed more checks than allowed. This run may be very long or flaky; diagnose it again, or raise the engine's check budget.",
  }),
  llm_not_configured: () => ({
    title: "The API has no model configured",
    fix: "The engine needs a model to rewrite and explain the step. Set the OpenAI key and engine models in server/.env, restart the API, then diagnose again.",
  }),
  llm_call_failed: () => ({
    title: "A model call failed",
    fix: "The model provider returned an error or timed out. Wait a moment, then diagnose the run again.",
  }),
  check_inconsistent: () => ({
    title: "Your success check passed the recorded run",
    fix: "A replay that kept every recorded step passed your success check, so the check does not reliably fail this run, or the world changed since it was recorded. No step can be blamed. Make the check fail this run every time, then diagnose it again.",
  }),
  replay_not_faithful: ({ driftToolName }) => ({
    title: "Replays did not match the recording",
    fix: `${driftToolName === null ? "A tool" : driftToolName} returned different data on replay than when the run was recorded, for example live data, the time or randomness, so no replay counted as evidence. Mark it with @fd.tool so replays reuse its recorded result, then diagnose the run again.`,
    code: `@fd.tool\ndef ${driftToolName ?? "your_tool"}(...): ...`,
  }),
  interrupted: () => ({
    title: "The API stopped while running this diagnosis",
    fix: "The API restarted or lost track of the diagnosis. Nothing is wrong with the run; diagnose it again to start a fresh search.",
  }),
  internal_error: () => ({
    title: "The diagnosis hit an unexpected error",
    fix: "Check the API logs for the error, then diagnose the run again.",
  }),
} as const satisfies Record<
  DiagnosisErrorCode,
  (context: DiagnosisErrorContext) => DiagnosisErrorCopy
>;

const UNKNOWN: DiagnosisErrorCopy = {
  title: "The diagnosis stopped before it named a step",
  fix: "Check that a replay worker is running for this agent and can reach the API, then diagnose the run again.",
};

export function diagnosisErrorCopy(
  code: DiagnosisErrorCode | null,
  context: DiagnosisErrorContext
): DiagnosisErrorCopy {
  return code === null ? UNKNOWN : COPY[code](context);
}
