import { describe, expect, it } from "vitest";

import type { Check, CheckPhase, CheckResult } from "@/api/generated";

import { checkResultStatus, checkRows } from "./check-rows";

function check(
  index: number,
  phase: CheckPhase,
  savePoint: number,
  passes: number,
  samples: number,
  result: CheckResult,
  drift: Pick<Check, "drifted" | "drift_tool_name"> = { drifted: 0, drift_tool_name: null }
): Check {
  return {
    id: `c${index}`,
    diagnosis_id: "d1",
    index,
    phase,
    save_point: savePoint,
    samples,
    passes,
    result,
    ...drift,
    created_at: "2026-11-21T18:00:00Z",
  } as Check;
}

describe("checkRows", () => {
  it("shows a rechecked save point as one row with every round counted", () => {
    const rows = checkRows([
      check(0, "bisect", 6, 1, 1, "can_succeed"),
      check(1, "bisect", 9, 0, 3, "doomed"),
      check(2, "bisect", 9, 0, 3, "doomed"),
      check(3, "bisect", 8, 0, 3, "doomed"),
      check(4, "bisect", 8, 1, 2, "can_succeed"),
      check(5, "verify", 6, 3, 3, "can_succeed"),
    ]);

    expect(
      rows.map((row) => [
        row.number,
        row.id,
        row.save_point,
        `${row.passes}/${row.samples}`,
        row.result,
      ])
    ).toEqual([
      [1, "c0", 6, "1/1", "can_succeed"],
      [2, "c1", 9, "0/6", "doomed"],
      [3, "c3", 8, "1/5", "can_succeed"],
      [4, "c5", 6, "3/3", "can_succeed"],
    ]);
    expect(rows[1]?.rounds.map((round) => round.id)).toEqual(["c1", "c2"]);
  });

  it("keeps a running second round running", () => {
    const [row] = checkRows([
      check(0, "bisect", 4, 0, 3, "doomed"),
      check(1, "bisect", 4, 0, 1, "pending"),
    ]);

    expect([row?.result, row?.passes, row?.samples]).toEqual(["pending", 0, 4]);
  });

  it("does not merge the same save point in different phases", () => {
    const rows = checkRows([
      check(0, "bisect", 3, 0, 6, "doomed"),
      check(1, "verify", 3, 3, 3, "can_succeed"),
    ]);

    expect(rows).toHaveLength(2);
  });

  it("adds up drifted replays across rounds and keeps the latest drifted tool", () => {
    const [row] = checkRows([
      check(0, "bisect", 4, 0, 2, "doomed", { drifted: 1, drift_tool_name: "lookup_order" }),
      check(1, "bisect", 4, 0, 3, "doomed", { drifted: 2, drift_tool_name: "get_time" }),
      check(2, "bisect", 4, 0, 3, "doomed"),
    ]);

    expect([row?.drifted, row?.drift_tool_name]).toEqual([3, "get_time"]);
  });
});

describe("checkResultStatus", () => {
  it("shows a running check as running", () => {
    expect(checkResultStatus({ result: "pending", finished_at: null }).label).toBe("Running");
  });

  it("shows a finished check with no usable replay as no verdict", () => {
    expect(
      checkResultStatus({ result: "pending", finished_at: "2026-11-21T18:00:05Z" }).label
    ).toBe("No verdict");
  });

  it("shows a decided check by its result", () => {
    expect(checkResultStatus({ result: "doomed", finished_at: "2026-11-21T18:00:05Z" }).label).toBe(
      "Doomed"
    );
  });
});
