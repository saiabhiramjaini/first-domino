import type {
  CauseCategory,
  CheckPhase,
  CheckResult,
  DiagnosisStatus,
  RunSource,
  RunStatus,
  VerdictKind,
} from "@/api/generated";

import type { ToneLabel } from "./tone";

export const RUN_STATUS = {
  running: { tone: "info", label: "Running" },
  passed: { tone: "success", label: "Passed" },
  failed: { tone: "danger", label: "Failed" },
  errored: { tone: "warning", label: "Errored" },
} as const satisfies Record<RunStatus, ToneLabel>;

export const RUN_SOURCE = {
  recorded: { tone: "neutral", label: "Recorded" },
  replay: { tone: "info", label: "Replay" },
} as const satisfies Record<RunSource, ToneLabel>;

export const DIAGNOSIS_STATUS = {
  queued: { tone: "neutral", label: "Queued" },
  bisecting: { tone: "info", label: "Bisecting" },
  verifying: { tone: "info", label: "Verifying the fix" },
  explaining: { tone: "info", label: "Explaining" },
  done: { tone: "success", label: "Done" },
  failed: { tone: "danger", label: "Diagnosis failed" },
} as const satisfies Record<DiagnosisStatus, ToneLabel>;

export const VERDICT_KIND = {
  step_verified: { tone: "success", label: "Verified" },
  step_unverified: { tone: "warning", label: "Not verified" },
  multiple_causes: { tone: "warning", label: "Multiple causes" },
  task_or_tool_issue: { tone: "neutral", label: "Task or tool issue" },
} as const satisfies Record<VerdictKind, ToneLabel>;

export const CHECK_PHASE = {
  precheck: { tone: "neutral", label: "Precheck" },
  bisect: { tone: "info", label: "Bisect" },
  verify: { tone: "success", label: "Verify" },
  fallback: { tone: "warning", label: "Fallback" },
} as const satisfies Record<CheckPhase, ToneLabel>;

export const CHECK_RESULT = {
  pending: { tone: "neutral", label: "Running" },
  can_succeed: { tone: "success", label: "Can succeed" },
  doomed: { tone: "domino", label: "Doomed" },
} as const satisfies Record<CheckResult, ToneLabel>;

export const CAUSE_CATEGORY = {
  wrong_date: { tone: "domino", label: "Wrong date" },
  wrong_entity: { tone: "domino", label: "Wrong entity" },
  wrong_filter: { tone: "domino", label: "Wrong filter" },
  bad_tool_args: { tone: "domino", label: "Bad tool arguments" },
  hallucination: { tone: "domino", label: "Hallucination" },
  tool_issue: { tone: "warning", label: "Tool issue" },
  other: { tone: "neutral", label: "Other" },
} as const satisfies Record<CauseCategory, ToneLabel>;
