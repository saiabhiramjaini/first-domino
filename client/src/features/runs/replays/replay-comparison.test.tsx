import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Check, Message, Run, Step } from "@/api/generated";

import { ReplayComparison } from "./replay-comparison";

const RUN_ID = "00000000-0000-4000-8000-000000000001";

function call(name: string, args: object): Message {
  return {
    role: "assistant",
    content: null,
    tool_calls: [{ id: `${name}-id`, name, arguments: JSON.stringify(args) }],
    tool_call_id: null,
  };
}

function step(runId: string, index: number, output: Message): Step {
  return {
    id: `${runId.slice(0, 30)}${String(index).padStart(6, "0")}`,
    run_id: runId,
    index,
    model: "m",
    output,
    tool_results: [],
    tokens_in: 1,
    tokens_out: 1,
    latency_ms: 1,
    created_at: "2026-11-21T00:00:00Z",
  };
}

function run(id: string, status: Run["status"]): Run {
  return {
    id,
    agent_name: "call-assistant",
    source: "replay",
    parent_run_id: RUN_ID,
    replay_job_id: null,
    replay_from_step: 1,
    task_input: { prompt: "Answer the call", metadata: {} },
    tool_names: [],
    status,
    step_count: 3,
    final_output: null,
    failure_reason: null,
    flagged_at: null,
    flagged_by_id: null,
    latest_diagnosis_id: null,
    created_by_id: RUN_ID,
    started_at: "2026-11-21T00:00:00Z",
    finished_at: null,
  };
}

function check(phase: Check["phase"]): Check {
  return {
    id: "00000000-0000-4000-8000-0000000000c1",
    diagnosis_id: RUN_ID,
    index: 5,
    phase,
    save_point: 1,
    samples: 2,
    passes: 1,
    result: "can_succeed",
    drifted: 0,
    drift_tool_name: null,
    created_at: "2026-11-21T00:00:00Z",
    finished_at: null,
  };
}

const original = [
  step(RUN_ID, 1, call("lookup_contact", { name: "Rao" })),
  step(RUN_ID, 2, call("add_calendar_event", { time: "22:00" })),
  step(RUN_ID, 3, call("send_summary", {})),
];
const sameId = "00000000-0000-4000-8000-0000000000a1";
const fixedId = "00000000-0000-4000-8000-0000000000a2";
const replays = [
  { run: run(sameId, "failed"), steps: original.map((s) => ({ ...s, run_id: sameId })) },
  {
    run: run(fixedId, "passed"),
    steps: [
      original[0]!,
      step(fixedId, 2, call("add_calendar_event", { time: "10:00" })),
      step(fixedId, 3, call("reply_to_caller", {})),
    ],
  },
];

describe("ReplayComparison", () => {
  it("shows each replay's outcome and marks where it diverges", () => {
    render(<ReplayComparison check={check("bisect")} originalSteps={original} replays={replays} />);
    expect(screen.getByText("1/2 replays passed")).toBeInTheDocument();
    expect(screen.getAllByText("Differs here")).toHaveLength(1);
    const row = screen.getByRole("rowheader", { name: "2" }).closest("tr");
    expect(row).not.toBeNull();
    expect(within(row as HTMLElement).getByText("Differs here")).toBeInTheDocument();
  });

  it("labels the rewritten step of a verify check", () => {
    render(<ReplayComparison check={check("verify")} originalSteps={original} replays={replays} />);
    expect(screen.getAllByText("Rewritten step")).toHaveLength(2);
    expect(screen.getByText("Keep step 1, then fixed step 2")).toBeInTheDocument();
  });
});
