import { describe, expect, it } from "vitest";

import { doneCount, onboardingItems } from "./onboarding";

function statuses(input: Parameters<typeof onboardingItems>[0]) {
  return Object.fromEntries(onboardingItems(input).map((item) => [item.id, item.status]));
}

describe("onboardingItems", () => {
  it("shows loading until the API answers", () => {
    expect(
      statuses({ hasActiveKey: undefined, recordedRuns: undefined, replayRuns: undefined })
    ).toEqual({ create_key: "loading", connect_agent: "loading", start_worker: "loading" });
  });

  it("ticks the key, then the first run, then the first replay", () => {
    expect(statuses({ hasActiveKey: true, recordedRuns: 0, replayRuns: 0 })).toEqual({
      create_key: "done",
      connect_agent: "todo",
      start_worker: "todo",
    });
    const all = onboardingItems({ hasActiveKey: true, recordedRuns: 3, replayRuns: 12 });
    expect(doneCount(all)).toBe(3);
  });
});
