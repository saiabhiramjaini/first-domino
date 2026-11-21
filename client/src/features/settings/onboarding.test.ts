import { describe, expect, it } from "vitest";

import { doneCount, onboardingItems } from "./onboarding";

function statuses(input: Parameters<typeof onboardingItems>[0]) {
  return Object.fromEntries(onboardingItems(input).map((item) => [item.id, item.status]));
}

describe("onboardingItems", () => {
  it("shows loading until the API answers", () => {
    expect(
      statuses({ hasActiveKey: undefined, recordedRuns: undefined, replayRuns: undefined })
    ).toEqual({
      create_key: "loading",
      install_sdk: "loading",
      record_run: "loading",
      start_worker: "loading",
    });
  });

  it("ticks the key first, then the SDK and run together, then the worker", () => {
    expect(statuses({ hasActiveKey: true, recordedRuns: 0, replayRuns: 0 })).toEqual({
      create_key: "done",
      install_sdk: "todo",
      record_run: "todo",
      start_worker: "todo",
    });
    const all = onboardingItems({ hasActiveKey: true, recordedRuns: 3, replayRuns: 12 });
    expect(doneCount(all)).toBe(4);
  });
});
