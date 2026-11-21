import type { DiagnosisErrorCode } from "@/api/generated";

export type DiagnosisErrorCopy = { title: string; fix: string };

const COPY = {
  replay_unavailable: {
    title: "No replay came back",
    fix: "Every replay of a check errored or timed out. Start a replay worker for this agent with fd.Worker, check it can reach the API, then diagnose the run again.",
  },
  check_budget_exceeded: {
    title: "The diagnosis ran out of checks",
    fix: "The search needed more checks than allowed. This run may be very long or flaky; diagnose it again, or raise the engine's check budget.",
  },
  llm_not_configured: {
    title: "The API has no model configured",
    fix: "The engine needs a model to rewrite and explain the step. Set the OpenAI key and engine models in backend/.env, restart the API, then diagnose again.",
  },
  llm_call_failed: {
    title: "A model call failed",
    fix: "The model provider returned an error or timed out. Wait a moment, then diagnose the run again.",
  },
  interrupted: {
    title: "The API restarted mid-diagnosis",
    fix: "Nothing is wrong with the run. Diagnose it again to start a fresh search.",
  },
  internal_error: {
    title: "The diagnosis hit an unexpected error",
    fix: "Check the API logs for the error, then diagnose the run again.",
  },
} as const satisfies Record<DiagnosisErrorCode, DiagnosisErrorCopy>;

const UNKNOWN: DiagnosisErrorCopy = {
  title: "The diagnosis stopped before it named a step",
  fix: "Check that a replay worker is running for this agent and can reach the API, then diagnose the run again.",
};

export function diagnosisErrorCopy(code: DiagnosisErrorCode | null): DiagnosisErrorCopy {
  return code === null ? UNKNOWN : COPY[code];
}
