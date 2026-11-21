import { describe, expect, it } from "vitest";

import type { Message, Step } from "@/api/generated";

import { comparedStepIndices, divergenceStep, messageSignature } from "./divergence";

function call(name: string, args: object): Message {
  return {
    role: "assistant",
    content: null,
    tool_calls: [{ id: `${name}-id`, name, arguments: JSON.stringify(args) }],
    tool_call_id: null,
  };
}

function step(index: number, output: Message): Step {
  return {
    id: `00000000-0000-4000-8000-${String(index).padStart(12, "0")}`,
    run_id: "00000000-0000-4000-8000-000000000000",
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

const original = [
  step(1, call("lookup_contact", { name: "Rao" })),
  step(2, call("add_calendar_event", { time: "22:00", date: "2026-11-22" })),
  step(3, call("send_summary", {})),
];

describe("messageSignature", () => {
  it("ignores argument order and tool call ids", () => {
    const a = call("add", { a: 1, b: 2 });
    const b: Message = {
      ...call("add", { b: 2, a: 1 }),
      tool_calls: [{ id: "other", name: "add", arguments: '{"b":2,"a":1}' }],
    };
    expect(messageSignature(a)).toBe(messageSignature(b));
  });
});

describe("divergenceStep", () => {
  it("finds the first step after the save point that differs", () => {
    const replay = [
      original[0]!,
      step(2, call("add_calendar_event", { date: "2026-11-22", time: "10:00" })),
      step(3, call("send_summary", {})),
    ];
    expect(divergenceStep(original, replay, 1)).toBe(2);
  });

  it("ignores differences inside the kept steps", () => {
    const replay = [step(1, call("other", {})), original[1]!, original[2]!];
    expect(divergenceStep(original, replay, 1)).toBeNull();
  });

  it("treats a missing or extra step as the divergence", () => {
    expect(divergenceStep(original, original.slice(0, 2), 1)).toBe(3);
    const longer = [...original, step(4, call("reply_to_caller", {}))];
    expect(divergenceStep(original, longer, 1)).toBe(4);
  });
});

describe("comparedStepIndices", () => {
  it("lists every step after the save point across all runs", () => {
    expect(comparedStepIndices([original, [step(5, call("x", {}))]], 2)).toEqual([3, 4, 5]);
  });
});
