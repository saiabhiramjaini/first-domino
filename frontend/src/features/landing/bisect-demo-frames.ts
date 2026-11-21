import type { CheckResult } from "@/api/generated";
import type { StripDiagnosis } from "@/components/runs/step-strip-state";

export const DEMO_STEP_COUNT = 12;
export const DEMO_FIRST_DOMINO = 7;

export type DemoCheck = { label: string; result: CheckResult; passed: string };

export type DemoFrame = {
  id: string;
  title: string;
  caption: string;
  diagnosis: StripDiagnosis | undefined;
  check: DemoCheck | null;
};

function bisecting(low: number, high: number): StripDiagnosis {
  return {
    status: "bisecting",
    search_low: low,
    search_high: high,
    first_domino_step: null,
    verdict_kind: null,
  };
}

export const DEMO_FRAMES: readonly DemoFrame[] = [
  {
    id: "recorded",
    title: "A call fails",
    caption:
      "The call assistant took 12 steps and booked the callback for the wrong day. The success check marks the run failed.",
    diagnosis: undefined,
    check: null,
  },
  {
    id: "precheck",
    title: "Can it succeed at all?",
    caption:
      "Replay from the task alone. Some replays succeed, so the task is fine: one of the 12 steps doomed this run.",
    diagnosis: bisecting(1, 12),
    check: { label: "Fresh run", result: "can_succeed", passed: "2 of 3" },
  },
  {
    id: "keep-6",
    title: "Keep steps 1 to 6",
    caption:
      "Keep the first 6 steps exactly as recorded and replay the rest. It can still succeed, so the first domino comes after step 6.",
    diagnosis: bisecting(7, 12),
    check: { label: "Keep steps 1 to 6", result: "can_succeed", passed: "1 of 3" },
  },
  {
    id: "keep-9",
    title: "Keep steps 1 to 9",
    caption: "Every replay fails. The run was already doomed by step 9.",
    diagnosis: bisecting(7, 9),
    check: { label: "Keep steps 1 to 9", result: "doomed", passed: "0 of 3" },
  },
  {
    id: "keep-7",
    title: "Keep steps 1 to 7",
    caption: "Still doomed, while 1 to 6 could succeed. Step 7 is the first domino.",
    diagnosis: {
      status: "verifying",
      search_low: DEMO_FIRST_DOMINO,
      search_high: DEMO_FIRST_DOMINO,
      first_domino_step: DEMO_FIRST_DOMINO,
      verdict_kind: null,
    },
    check: { label: "Keep steps 1 to 7", result: "doomed", passed: "0 of 3" },
  },
  {
    id: "verified",
    title: "Prove it with a fix",
    caption:
      "Rewrite only step 7 to ask for the right Tuesday, then replay. The run now passes: the cause is proven, not guessed.",
    diagnosis: {
      status: "done",
      search_low: DEMO_FIRST_DOMINO,
      search_high: DEMO_FIRST_DOMINO,
      first_domino_step: DEMO_FIRST_DOMINO,
      verdict_kind: "step_verified",
    },
    check: { label: "Fixed step 7", result: "can_succeed", passed: "4 of 5" },
  },
];
